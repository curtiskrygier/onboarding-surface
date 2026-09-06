# serve — the A2A wrapper (spec §12)

A stateless A2A service: `author`/`render`/`draw` over one call each, or all
three chained (`full`). The server never touches a caller's git checkout —
`extract` stays something the caller runs locally (that's its whole contract);
the caller sends the resulting `facts.json`, and optionally a pre-built text
digest, over the wire.

```
python3 -m serve                                # PORT env var, default 8080
ONBOARDING_SURFACE_TOKEN=secret python3 -m serve   # require a bearer token
```

## Skills

| skill | needs | cost |
|---|---|---|
| `author` | `facts` (+ optional `digest`) | one LLM call — `MAISON_GEMINI_API_KEY` server-side |
| `render` | `facts` (+ optional `authored`) | none — pure templating, always `--fresh` |
| `draw` | `facts` | none — the `d2` CLI, no LLM |
| `full` | `facts` (+ optional `digest`) | chains all three — can take 60–90s |

Split into separate skills rather than one `mode=check|full` call (as
`docs/design.md` originally sketched) because a sync HTTP call batching two
LLM steps together is fragile: a proxy or client timeout mid-call burns real
spend for a caller who gets nothing back (Gemini 3.8 Flash design review,
2026-09-06). `full` still exists for a caller who's already sized their own
timeouts for it.

## Calling it

```python
import httpx
from author.author import build_digest
from serve.client import call_agent

facts = json.loads(open("facts.json").read())
digest = build_digest(Path(facts["_repo_path"]), facts)  # only needed for author/full

async with httpx.AsyncClient(base_url="https://your-serve-instance") as hc:
    result = await call_agent(hc, "full", facts=facts, digest=digest,
                              author=True, exposure="public", art=True)
# result: {"docs": {...}, "authored": {...}, "sketch_svg": "<svg ...>"}
```

If the server has `ONBOARDING_SURFACE_TOKEN` set, put `Authorization: Bearer
<token>` on the `httpx.AsyncClient` itself — every request it makes then
carries it (see `client.py`'s docstring).

## Revised from `docs/design.md`'s original sketch

The original design had the caller bundle a raw file slice and the **server**
run `extract` over it. `extract` as actually built is a `git`-checkout tool
(`git ls-files`, `git log` for history/contrib facts) — reimplementing it to
work off an uploaded bundle would duplicate that logic against a shakier
input, and (Gemini 3.8 Flash design review, 2026-09-06) reopens exactly the
security surface a stateless, repo-blind server was meant to avoid: SSRF via
clone, credential delegation, disk cleanup. The caller already needs a local
checkout to run `extract` at all — sending its output is strictly less
exposure than sending the repo.

## Protection

Reviewed with Gemini 3.8 Flash (2026-09-06) against "this can trigger a real
LLM call and a subprocess exec per message, with no auth in the minimal
version" — verdict: proportionate for a solo experimentation repo, not a
product, but not nothing:

- **`MAX_PAYLOAD_BYTES` (512 KB)** — rejected before parsing.
- **A static bearer token** (`ONBOARDING_SURFACE_TOKEN`) — a no-op when unset
  (local/dev default), enforced by `_BearerAuthMiddleware` when set.
- **`render_d2`'s existing subprocess timeout** (`draw.py`) — a real CLI
  invocation with a fixed arg list, never raw flags from the caller's payload.

Explicitly deferred (not oversight): rate limiting, OAuth/OIDC, a sandboxed
`d2` execution environment.

## Verified 2026-09-06

In-process (`httpx.ASGITransport`, real `a2a-sdk` client and server, see
`test_serve.py`, `python3 -m pytest serve/test_serve.py -q`): `render`
round-trips real docs; the public-exposure filter holds identically to the
CLI (a fabricated private clone_gap lands in `MAINTAINER-NOTES.md`, never in
the three public docs); `draw` returns a real D2 SVG with no LLM call;
missing `facts` and an oversized payload both reply with a clear error
instead of a crash; the bearer-auth middleware rejects an unauthenticated
request when a token is configured, accepts one with the right header.

Manual (real API cost, not in the automated suite): the `full` job chaining
a live `author` call + `render` + `draw` against `a2ui-catalogue`'s real
facts — public exposure held (`ops.py` absent from the three docs, present
only in `MAINTAINER-NOTES.md`); `author` alone with no `digest` supplied
degrades to facts-only authoring rather than failing; an unknown job name is
rejected with a clear message, not a crash.
