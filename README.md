<img src="assets/logo.svg" alt="" width="60">

# onboarding-surface

**Experimental, solo-built, no stability guarantees.** This is a personal
exploration of what a truth-guaranteed onboarding-doc pipeline can look like —
every module in this repo is real and verified against real repos (see each
module's own `README.md`), but interfaces, prompts and the spec itself are
still moving. Not a maintained product; use it as a reference or fork it, but
don't expect semver or a support channel.

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
| `action/` | Step 6, §11 — the CI adapter: `uses: curtiskrygier/onboarding-surface/action@v1` in a consuming repo's own workflow. Formatter, not gate. |
| `examples/` | The original hand-worked surface that pressure-tested the spec before any code existed. |

Each module's own `README.md` has its CLI and what's verified so far.

## Status

`extract` → `author` → `render` → `draw` → `review` → `serve` all built and
verified on real repos (a2ui-catalogue, maison, onboarding-surface itself).
`serve` is a real A2A service (`author`/`render`/`draw`/`full` skills) — see
`serve/README.md`. `action/` (the CI-formatter GitHub Action) is also built —
see `action/README.md` for how to wire it into a consuming repo's workflow.

## Where it fits

A standalone build repo — nothing here depends on where it's deployed or used
from. In the author's own setup it also feeds a separate, private
experimentation repo that onboards other agents and tools and harvests
reusable patterns across them; that repo isn't part of this one's contract.

<!-- onboarding-surface:begin what-it-is -->
<!-- authored: pending — run `python3 -m author` -->
<!-- onboarding-surface:end what-it-is -->

<!-- onboarding-surface:begin maturity -->
quiet — a few commits in the last 90 days; CI: docs.yml.
<!-- onboarding-surface:end maturity -->

<!-- onboarding-surface:begin orientation -->
<!-- authored: pending — run `python3 -m author` -->
<!-- onboarding-surface:end orientation -->

<!-- onboarding-surface:begin run-it -->
This repo is a **toolkit** — there is no server to start. "Running it" means the build/test pipeline below.

**System prerequisites:** `python` 3.11.

**Environment:** none declared.

```
pip install -r requirements.txt
```

Test: `python3 -m pytest`
<!-- onboarding-surface:end run-it -->

<!-- onboarding-surface:begin pointers -->
- `ARCHITECTURE.md` — the codemap and landmines
- `CONTRIBUTING.md` — how to get a PR merged
- `spec/` — internal contracts
- `docs/` — deeper docs
<!-- onboarding-surface:end pointers -->
