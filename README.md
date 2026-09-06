<img src="assets/logo.svg" alt="" width="60">

# onboarding-surface

An agent that turns a repository into a **contributor onboarding surface** — the
docs a new contributor needs to go from `git clone` to a merged first PR, kept
true as the code changes.

Primary output is lean, truth-guaranteed Markdown: `README.md`, `ARCHITECTURE.md`,
`CONTRIBUTING.md`. An optional interactive surface (progress-tracked walkthrough,
"document that learns" analytics) is a later, separate concern — not the pitch.

## The one rule

**Never fabricate.** "Verification command: UNKNOWN (not found in repo)" beats an
invented `npm test` that breaks. Every section is either mechanically derived and
verifiable, or explicitly marked *authored, unverified*.

## How it's structured

| Piece | What it is |
|---|---|
| `spec/onboarding-surface-v0.1.md` | The contract — section catalogue, deterministic vs authored split, extraction sources, exposure/landmine classification (§15), visuals (§16). Everything generates from this. |
| `extract/` | Step 1 — `facts.json` from a repo. Offline by default; `--github` adds an online adapter. |
| `author/` | Step 2 — the one governed LLM call: `facts.json` → authored prose + classified landmine records. |
| `render/` | Step 3 — `facts.json` (+ authored) → `README.md` / `ARCHITECTURE.md` / `CONTRIBUTING.md` (+ `MAINTAINER-NOTES.md` in `--exposure public`). |
| `draw/` | §16b, cadence-only — `facts.json` → a structured architecture-sketch prompt → a sanitised, cached SVG, embedded by `render`. |
| `review/` | The HITL review page — read-only, no approve/reject gate. |
| `examples/` | The original hand-worked surface that pressure-tested the spec before any code existed. |

Each module's own `README.md` has its CLI and what's verified so far.

## Status

`extract` → `author` → `render` → `draw` → `review` all built and verified on
real repos (a2ui-catalogue, maison, onboarding-surface itself). No A2A service
wrapper or GitHub Action yet — see "Where it fits" below and
`agentic-battle-testing/scripts/onboard.py`, which runs the pipeline end-to-end
against an onboarded repo today.

## Where it fits

Standalone build repo. Once it's a live A2A agent it gets an entry in
`agentic-battle-testing`'s Agents inventory; its extracted patterns are harvested
into that repo's Tools section.
