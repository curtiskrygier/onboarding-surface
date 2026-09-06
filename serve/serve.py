"""serve.py — the A2A wrapper (spec §12): lets a remote caller run
author/render/draw over one A2A call, without the server ever touching the
caller's git checkout.

Modeled on a sibling repo's own real A2A service (same AgentCard/
AgentExecutor/A2AStarletteApplication/DefaultRequestHandler/uvicorn.run
shape) — trimmed to a bare, stateless request/reply executor (no Task
lifecycle, no per-conversation state; every call is independent).

REVISED SPLIT (2026-09-06) from docs/design.md's original sketch: that
proposal had the caller bundle a raw file slice and the SERVER run `extract`
over it. `extract` as actually built is a `git`-checkout tool (git ls-files,
git log for history/contrib facts) — reimplementing it to work off an
uploaded bundle would duplicate that logic for a shakier input, and (Gemini
3.8 Flash design review, 2026-09-06) reopens exactly the security surface a
stateless, repo-blind server was meant to avoid: SSRF via clone, credential
delegation, disk cleanup. So: **the caller runs `extract` locally** (already
its whole contract) and sends the resulting `facts.json`, plus an optional
pre-built `author.build_digest()` string, over one A2A message. The server
is a pure `(facts, digest, options) -> (docs, sketch)` transform — no git,
no filesystem state, no credentials.

Split into skills instead of one `mode=check|full` call (same review, on
author+render+draw batched into one 60-90s round trip: proxies commonly drop
sync connections well under that, and a network blip mid-call burns real LLM
spend for a caller who gets nothing back). `author`, `render`, and `draw`
are independently callable; `full` chains them for a caller who has already
weighed that tradeoff.

    python3 -m serve                       # PORT env var, default 8080
    ONBOARDING_SURFACE_TOKEN=... python3 -m serve   # require a bearer token
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities, AgentCard, AgentSkill, DataPart, Part, TextPart,
)
from a2a.utils import new_agent_parts_message

from author.author import build_authored
from draw.draw import D2Error, build_d2_source, build_diagram_spec, render_d2
from render.render import render

AGENT_BASE_URL = os.environ.get("ONBOARDING_SURFACE_URL", "http://localhost:8080/")
# Gemini 3.8 Flash design review, 2026-09-06: reject an oversized payload
# before it's even parsed, not after — cheap DoS protection for a
# single-instance solo deployment.
MAX_PAYLOAD_BYTES = 512_000
_JOBS = ("author", "render", "draw", "full")


def _reply_error(event_queue, context, message: str):
    return event_queue.enqueue_event(new_agent_parts_message(
        [Part(root=TextPart(text=message))], context.context_id, context.task_id))


class OnboardingSurfaceExecutor(AgentExecutor):
    """Stateless: every `execute()` call is independent, nothing is kept
    between messages (unlike the sibling repo's own stateful surface
    executor — there is no surface here, no conversation to accumulate)."""

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        data_part = next(
            (getattr(p, "root", p) for p in (context.message.parts or [])
             if isinstance(getattr(p, "root", p), DataPart)),
            None,
        )
        if data_part is None:
            await _reply_error(event_queue, context,
                              "No DataPart found on the incoming message — "
                              "expected {job, facts, ...}.")
            return

        payload = data_part.data
        raw_len = len(json.dumps(payload))
        if raw_len > MAX_PAYLOAD_BYTES:
            await _reply_error(event_queue, context,
                              f"payload too large ({raw_len} bytes > {MAX_PAYLOAD_BYTES})")
            return

        job = payload.get("job")
        if job not in _JOBS:
            await _reply_error(event_queue, context,
                              f"job must be one of {_JOBS}, got {job!r}")
            return
        facts = payload.get("facts")
        if not isinstance(facts, dict):
            await _reply_error(event_queue, context,
                              "facts (a facts.json object from `extract`) is required")
            return

        exposure = payload.get("exposure", "internal")
        result: dict = {"job": job}
        try:
            authored = None
            if job in ("author", "full"):
                authored = build_authored(
                    facts, model=payload.get("model", "gemini-3.8-flash"),
                    exposure=exposure, digest=payload.get("digest"))
                result["authored"] = authored
            elif payload.get("authored"):
                authored = payload["authored"]

            if job in ("render", "full"):
                # server-side is always --fresh: there is no target repo
                # here to splice into (Gemini review, 2026-09-06 — splicing
                # is trivially the CALLER's job, it already has the checkout).
                result["docs"] = render(facts, authored or {}, exposure=exposure, fresh=True)

            if job in ("draw", "full"):
                spec = build_diagram_spec(facts, exposure=exposure,
                                         detail=payload.get("detail", "overview"))
                with tempfile.TemporaryDirectory() as td:
                    out = Path(td) / "sketch.svg"
                    render_d2(build_d2_source(spec), out)
                    result["sketch_svg"] = out.read_text()
        except D2Error as e:
            await _reply_error(event_queue, context, f"draw failed: {e}")
            return
        except Exception as e:  # noqa: BLE001 — a caller error surfaces as text, not a 500
            await _reply_error(event_queue, context, f"{job} failed: {e}")
            return

        reply = Part(root=DataPart(data=result))
        await event_queue.enqueue_event(new_agent_parts_message(
            [reply], context.context_id, context.task_id))

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise Exception("cancel not supported — every call is a single synchronous job")


class _BearerAuthMiddleware:
    """Raw ASGI middleware (not Starlette's `Middleware(...)` list — that
    only composes at app-construction time, and this needs to wrap the
    ALREADY-built A2AStarletteApplication, routes and all) checking a static
    shared secret. A no-op when ONBOARDING_SURFACE_TOKEN is unset — the
    default for local/dev use; Gemini 3.8 Flash design review, 2026-09-06:
    "you cannot leave this open unauthenticated" once actually deployed
    somewhere reachable, but a static bearer token is proportionate for a
    solo experimentation repo — OAuth/OIDC and rate limiting are explicitly
    deferred, not missing by oversight."""

    def __init__(self, app, token: str | None):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if self.token is None or scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        auth = headers.get(b"authorization", b"").decode(errors="replace")
        if auth == f"Bearer {self.token}":
            await self.app(scope, receive, send)
            return
        await send({"type": "http.response.start", "status": 401,
                   "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"missing or invalid bearer token"})


_SKILLS = [
    AgentSkill(id="author", name="Author onboarding prose",
              description="facts.json (+ a repo-text digest) -> authored README/ARCHITECTURE/"
                          "CONTRIBUTING prose and classified landmine records. Needs "
                          "MAISON_GEMINI_API_KEY server-side.",
              tags=["onboarding-surface", "llm"], examples=[]),
    AgentSkill(id="render", name="Render onboarding docs",
              description="facts.json (+ optional authored records) -> README.md/ARCHITECTURE.md/"
                          "CONTRIBUTING.md (+MAINTAINER-NOTES.md in public exposure). "
                          "Pure deterministic templating, always fresh (no splicing).",
              tags=["onboarding-surface", "deterministic"], examples=[]),
    AgentSkill(id="draw", name="Draw the architecture sketch",
              description="facts.json -> an architecture-sketch SVG via D2. Deterministic, "
                          "no LLM call. Needs the `d2` CLI server-side.",
              tags=["onboarding-surface", "deterministic", "d2"], examples=[]),
    AgentSkill(id="full", name="Full onboarding surface",
              description="Chains author -> render -> draw in one call. Slower (each LLM "
                          "step can take 60-90s) -- prefer the individual skills unless "
                          "you've already sized your own client/proxy timeouts for it.",
              tags=["onboarding-surface"], examples=[]),
]

agent_card = AgentCard(
    name="onboarding-surface",
    description="Turns a repo's facts.json (produced locally by `extract` -- this "
                "service never clones or reads a caller's repo) into contributor "
                "onboarding docs: authored prose, rendered Markdown, and an "
                "architecture sketch. Stateless -- one call, one job, no memory "
                "between calls.",
    url=AGENT_BASE_URL,
    version="0.1.0",
    default_input_modes=["application/json"],
    default_output_modes=["application/json"],
    capabilities=AgentCapabilities(streaming=False),
    skills=_SKILLS,
)

executor = OnboardingSurfaceExecutor()

_raw_app = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=DefaultRequestHandler(agent_executor=executor, task_store=InMemoryTaskStore()),
).build()

app = _BearerAuthMiddleware(_raw_app, token=os.environ.get("ONBOARDING_SURFACE_TOKEN"))
