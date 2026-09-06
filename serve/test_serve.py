"""Real A2A round-trip tests: a real a2a-sdk CLIENT (serve.client.call_agent)
talking to a real a2a-sdk SERVER (serve.serve.app), in-process via
httpx.ASGITransport — no network, no deployed service, no API key needed for
the jobs exercised here. Same pattern a sibling repo's own real A2A service
uses for its interop tests.

Plain sync test functions wrapping `asyncio.run()` rather than pytest-asyncio
— this repo's own stated preference (`author/vendor_vertex_rest.py`'s
docstring) is stdlib-first, no dependency added just to await inside a test.

`author`/`full` (the LLM-calling jobs) are deliberately NOT exercised here —
real API cost on every test run isn't proportionate for this repo's own
test-running habits (verified manually instead, see serve/README.md). `render`
and `draw` cover the actual server-side orchestration logic (payload parsing,
job dispatch, error replies) for free.

    python3 -m pytest serve/test_serve.py -q
"""
from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path

import httpx

from serve.client import call_agent

_FACTS_PATH = Path(__file__).resolve().parent.parent / "results/facts/onboarding-surface.json"


def _facts() -> dict:
    return json.loads(_FACTS_PATH.read_text())


def _run(coro):
    return asyncio.run(coro)


def test_render_job_round_trips_real_docs():
    from serve.serve import app

    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://serve.local") as hc:
            return await call_agent(hc, "render", facts=_facts(), exposure="internal")

    result = _run(go())
    assert set(result["docs"]) == {"README.md", "ARCHITECTURE.md", "CONTRIBUTING.md"}
    assert result["docs"]["README.md"].startswith("# ")


def test_render_public_exposure_holds_the_same_filter_as_the_cli():
    from serve.serve import app

    facts = _facts()
    # a fabricated clone_gap so this test doesn't depend on onboarding-surface
    # itself ever having a real private-ref to exercise the filter against
    facts["clone_gaps"].append({"path": "ops/secret-runbook.md", "in": "CLAUDE.md", "why": "gitignored"})

    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://serve.local") as hc:
            internal = await call_agent(hc, "render", facts=facts, exposure="internal")
            public = await call_agent(hc, "render", facts=facts, exposure="public")
        return internal, public

    internal, public = _run(go())
    assert "secret-runbook.md" in internal["docs"]["README.md"]
    # MAINTAINER-NOTES.md is WHERE it's supposed to end up in public mode
    # (spec §15) -- the invariant under test is that the three PUBLIC docs
    # never name it, not that it vanishes from the whole payload.
    public_docs = {k: v for k, v in public["docs"].items() if k != "MAINTAINER-NOTES.md"}
    assert "secret-runbook.md" not in json.dumps(public_docs)
    assert "secret-runbook.md" in public["docs"].get("MAINTAINER-NOTES.md", "")


def test_draw_job_returns_a_real_svg_with_no_llm_call():
    from serve.serve import app

    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://serve.local") as hc:
            return await call_agent(hc, "draw", facts=_facts())

    result = _run(go())
    # d2's own output leads with an XML declaration before <svg> -- unlike
    # the old freeform_canvas path, this isn't onboarding-surface's own
    # markup to control the exact prefix of.
    assert "<svg" in result["sketch_svg"][:120]


def test_missing_facts_replies_with_a_text_error_not_a_crash():
    from serve.serve import app

    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://serve.local") as hc:
            return await call_agent(hc, "render", facts=None)

    try:
        _run(go())
        raised = False
    except RuntimeError as e:
        raised = "facts" in str(e)
    assert raised


def test_oversized_payload_is_rejected():
    from serve.serve import MAX_PAYLOAD_BYTES, app

    facts = _facts()
    facts["_padding"] = "x" * (MAX_PAYLOAD_BYTES + 1000)

    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://serve.local") as hc:
            return await call_agent(hc, "render", facts=facts)

    try:
        _run(go())
        raised = False
    except RuntimeError as e:
        raised = "too large" in str(e)
    assert raised


def test_bearer_auth_middleware_rejects_without_a_token(monkeypatch):
    monkeypatch.setenv("ONBOARDING_SURFACE_TOKEN", "s3cret")
    import serve.serve as serve_mod
    importlib.reload(serve_mod)

    async def go():
        transport = httpx.ASGITransport(app=serve_mod.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://serve.local") as hc:
            unauthed = await hc.get("/.well-known/agent-card.json")
            hc.headers["Authorization"] = "Bearer s3cret"
            authed = await hc.get("/.well-known/agent-card.json")
        return unauthed, authed

    try:
        unauthed, authed = _run(go())
        assert unauthed.status_code == 401
        assert authed.status_code == 200
    finally:
        monkeypatch.delenv("ONBOARDING_SURFACE_TOKEN", raising=False)
        importlib.reload(serve_mod)
