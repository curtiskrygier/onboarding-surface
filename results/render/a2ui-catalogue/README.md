# a2ui

<!-- onboarding-surface:begin what-it-is -->
a2ui is a typed UI vocabulary and MCP server toolkit for AI agents. It provides a catalogue of over 450 UI atoms that agents can compose into rendered interfaces across surfaces such as web, Google Meet, Apps Script, Google Chat, and MCP Apps without requiring an account signup.
<!-- onboarding-surface:end what-it-is -->

<!-- onboarding-surface:begin maturity -->
near-daily — 479 commits in the last 90 days; latest release `v1.0.2`; CI: build-apps.yml, deploy.yml, gemini-review.yml, release-renderer.yml.
<!-- onboarding-surface:end maturity -->

<!-- onboarding-surface:begin orientation -->
The repository is declarative-first: state, policy, and processes are defined in manifests (`project.yaml`) with renderer source acting as the ultimate ground truth whenever documentation or schemas diverge.
It exists to provide a standardized, cross-surface interface vocabulary that prevents UI drift and ad-hoc improvisations across agent runtimes.
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

This standalone checkout is incomplete on its own: operational tools under `ops/`, incident notes, and benchmark files are untracked symlinks to the sibling repository `a2ui-private`. Commands relying on `python3 ops/ops.py` will fail unless the sibling private repo is cloned and its bootstrap run. Operational success means running operations solely through declared entries in `project.yaml`.
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
