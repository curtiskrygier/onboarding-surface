<!-- Worked example — how a2uicatalog/a2ui's onboarding README *should* read per
     spec v0.1. Hand-authored to pressure-test the spec, not generated. The real
     repo's README is marketing-first; this is contributor-first. -->

# a2ui — typed UI vocabulary for AI agents

<!-- onboarding-surface:begin what-it-is -->
A catalogue of **474 UI atoms** an AI agent composes into rendered interfaces —
across web, Google Meet, Apps Script, Google Chat, Slack and MCP Apps. The agent
names an atom and fills in a few fields; a renderer produces the HTML/card/markup
for the target surface. Ships an MCP server (`a2uicatalog.ai/mcp`, no signup).

Independent, unofficial — not affiliated with Google. A2UI is Google's protocol;
the spec lives at [a2ui.org](https://a2ui.org). This repo is the vocabulary layer
plus renderers.

**For you if** you're wiring an agent to emit real UI, or extending the atom set.
<!-- onboarding-surface:end what-it-is -->

## Status

<!-- onboarding-surface:begin maturity -->
Active — near-daily commits (478 in the last 90 days), latest release `v1.0.2`.
The spec is a v1.0 *candidate*. Production surfaces (`a2uicatalog.ai`, the MCP
endpoint) deploy from `main` via CI.
<!-- onboarding-surface:end maturity -->

## Orientation

<!-- onboarding-surface:begin orientation -->
The problem this solves: an agent generating UI from scratch every turn is
expensive, inconsistent, and un-reusable. Here the design decisions are
*pre-compiled* into the renderer once. The agent only picks atoms and supplies
content.

One mental model to hold: **`atoms/schema.yaml` is the source of truth.**
Almost everything else in the repo — `public/`, the JSON schemas, the compat
matrix, the MCP bundle, the builder prompts — is *generated from it* and must
not be hand-edited. Changing the catalogue means editing `schema.yaml` and
re-running the generators.

Why it exists rather than using an existing component library: those assume a
live React runtime. This targets the *constrained* surfaces (Meet Stage, Chat
cards, Apps Script) where CDN scripts and build pipelines don't exist.
<!-- onboarding-surface:end orientation -->

## Run it

<!-- onboarding-surface:begin run-it -->
There is no server to start locally — the product is a catalogue + generators +
deployed renderers. "Running it" means the generator/test pipeline.

**System prerequisites:** Python 3.11+, and a `node` binary on `PATH` (a real
subprocess call in ~9 tests that exercise the compiled JS renderer bundle — not
a pip package).

**Install:**
```
pip install -r requirements.txt      # pytest, pyyaml, markdown, jsonschema
```

**Test:**
```
python3 -m pytest tests/ -q          # ~741 tests, ~2.5 min
```

**Regenerate everything from `schema.yaml`:** `UNKNOWN from a public clone.` The
declared-process runner (`ops/ops.py`) lives in the **private** `ops/` tier and
is not in a public checkout. `CLAUDE.md` documents `python3 ops/ops.py run
catalog-rebuild` as the way, but that path does not exist here. What a public
contributor runs instead — the individual `scripts/gen_*.py` in order, or a
public shim — is not documented. Ask a maintainer, or see `ARCHITECTURE.md` →
Landmines.

**Environment:** none. No `.env`. Secrets for the deployed surfaces live in
Google Secret Manager / Apps Script Properties, out of the repo.
<!-- onboarding-surface:end run-it -->

## Pointers

<!-- onboarding-surface:begin pointers -->
- `ARCHITECTURE.md` — the codemap and the landmines (read before changing code)
- `CONTRIBUTING.md` — how to get a PR merged here
- `spec/` — internal state/action contracts; the A2UI v1.0 candidate spec is at
  [a2ui.org](https://a2ui.org/specification/v1.0-a2ui/), not vendored
- `CLAUDE.md` / `AGENTS.md` — the operating rules (also the best landmine source)
- Live: [a2uicatalog.ai](https://a2uicatalog.ai) · [/mcp](https://a2uicatalog.ai/mcp) · [spec.json](https://a2uicatalog.ai/spec.json)
- `a2uithoughts.md` — design rationale + incident history. **Gitignored — not in a clone.**
<!-- onboarding-surface:end pointers -->
