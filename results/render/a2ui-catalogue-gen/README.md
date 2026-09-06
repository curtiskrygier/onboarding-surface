# a2ui

<!-- onboarding-surface:begin what-it-is -->
a2ui is a toolkit and declarative UI catalogue providing UI atoms and renderers across multiple surfaces (such as Google Apps Script and Cloud Run) to allow AI agents to render rich visual components and interfaces.
<!-- onboarding-surface:end what-it-is -->

<!-- onboarding-surface:begin maturity -->
near-daily — 478 commits in the last 90 days; latest release `v1.0.2`; CI: build-apps.yml, deploy.yml, gemini-review.yml, release-renderer.yml.
<!-- onboarding-surface:end maturity -->

<!-- onboarding-surface:begin orientation -->
The repository operates under a strict declarative-first architecture where state, policy, inventory, and lifecycle processes are defined in manifest configurations rather than procedural script commands.

The project exists to provide a standardised, cross-surface declarative component vocabulary so autonomous agents can present visual surfaces without bespoke frontend logic.
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

Clone the private sibling repository `a2ui-private` alongside this repo and link its components (`ops/`, `thoughts/`, `a2uithoughts.md`, `improve.yaml`), as standalone clones lack the private operational scripts. Running `pip install -r requirements.txt` prepares dependencies; execute declared processes using `python3 ops/ops.py run <process>` rather than ad-hoc scripts. Success produces recorded runs in `ops/log.jsonl` without uncommitted drift.
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
