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
| `spec/onboarding-surface-v0.1.md` | The contract — section catalogue, deterministic vs authored split, extraction sources, anti-fabrication rules. Everything generates from this. |
| `examples/` | Hand-worked surfaces for real repos — pressure-tests the spec before code exists. |
| `docs/design.md` | The service shape: A2A endpoint, the CI-as-formatter mechanic, hosting. |

## Status

Spec + worked examples only. No service yet.

## Where it fits

Standalone build repo. Once it's a live A2A agent it gets an entry in
`agentic-battle-testing`'s Agents inventory; its extracted patterns are harvested
into that repo's Tools section.
