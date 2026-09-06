# a2ui

<!-- onboarding-surface:begin what-it-is -->
A catalogue of **474 UI atoms** an AI agent composes into rendered interfaces — across web, Google Meet, Apps Script, Google Chat, Slack and MCP Apps. The agent names an atom and fills in a few fields; a renderer produces the markup for the target surface. Ships an MCP server (`a2uicatalog.ai/mcp`, no signup).

Independent, unofficial — not affiliated with Google.

**For you if** you're wiring an agent to emit real UI, or extending the atom set.
<!-- onboarding-surface:end what-it-is -->

<!-- onboarding-surface:begin maturity -->
near-daily — 478 commits in the last 90 days; latest release `v1.0.2`; CI: build-apps.yml, deploy.yml, gemini-review.yml, release-renderer.yml.
<!-- onboarding-surface:end maturity -->

<!-- onboarding-surface:begin orientation -->
One mental model to hold: **`atoms/schema.yaml` is the source of truth.** `public/`, the JSON schemas, the compat matrix, the MCP bundle — all *generated from it*, not hand-edited. Changing the catalogue means editing `schema.yaml` and re-running the generators.
<!-- onboarding-surface:end orientation -->

<!-- onboarding-surface:begin run-it -->
This repo is a **toolkit** — there is no server to start. "Running it" means the build/test pipeline below.

**System prerequisites:** a `node` binary on `PATH` (real subprocess in tests).

**Environment:** none declared.

```
pip install -r requirements.txt
```

Test: `python3 -m pytest`

> **UNKNOWN** — regenerate/build from a clone: the docs reference `ops.py` which is absent — ask a maintainer.

**Sibling repos:** some processes need `../a2ui-private` checked out alongside.

<!-- authored: pending — run `python3 -m author` -->
<!-- onboarding-surface:end run-it -->

<!-- onboarding-surface:begin pointers -->
- `spec/` — internal contracts
- `CLAUDE.md` — operating rules (and the best landmine source)
- `AGENTS.md` — operating rules (and the best landmine source)
- `GEMINI.md` — operating rules (and the best landmine source)
- `docs/` — deeper docs
- `a2uithoughts.md` — referenced in CLAUDE.md but **gitignored, not in a clone**
- `improve.yaml` — referenced in AGENTS.md but **gitignored, not in a clone**
<!-- onboarding-surface:end pointers -->
