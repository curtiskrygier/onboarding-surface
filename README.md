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
| `draw/` | §16b/§16c — the architecture sketch (D2, deterministic, cadence-only) and repo-mark proposals (LLM, human-gated). |
| `review/` | The HITL review page — read-only, no approve/reject gate. |
| `serve/` | Step 5, §12 — the A2A wrapper: `author`/`render`/`draw`/`full` as remote skills. Stateless, repo-blind. |
| `examples/` | The original hand-worked surface that pressure-tested the spec before any code existed. |

Each module's own `README.md` has its CLI and what's verified so far.

## Status

`extract` → `author` → `render` → `draw` → `review` → `serve` all built and
verified on real repos (a2ui-catalogue, maison, onboarding-surface itself).
`serve` is a real A2A service (`author`/`render`/`draw`/`full` skills) — see
`serve/README.md`. No CI-formatter GitHub Action yet — see "Where it fits"
below and `agentic-battle-testing/scripts/onboard.py`, which runs the pipeline
end-to-end locally against an onboarded repo today.

## Where it fits

Standalone build repo. Once it's a live A2A agent it gets an entry in
`agentic-battle-testing`'s Agents inventory; its extracted patterns are harvested
into that repo's Tools section.
