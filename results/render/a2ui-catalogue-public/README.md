# a2ui

<!-- onboarding-surface:begin what-it-is -->
a2ui is a typed UI vocabulary and specification for AI agents implementing the a2ui protocol, providing atomic interface components that agents compose into rendered surfaces across web, Google Meet, Google Chat, Google Apps Script, and Model Context Protocol (MCP) environments.
<!-- onboarding-surface:end what-it-is -->

<!-- onboarding-surface:begin maturity -->
near-daily — 479 commits in the last 90 days; latest release `v1.0.2`; CI: build-apps.yml, deploy.yml, gemini-review.yml, release-renderer.yml.
<!-- onboarding-surface:end maturity -->

<!-- onboarding-surface:begin orientation -->
The repository operates under a strict declarative-manifest model where renderer implementations are the ground truth over documentation schemas, and deployment reachability must always be verified directly against live surfaces.
It exists to provide an open, standardized generative UI vocabulary so autonomous agents can render interactive interfaces without proprietary lock-in.
<!-- onboarding-surface:end orientation -->

<!-- onboarding-surface:begin run-it -->
This repo is a **toolkit** — there is no server to start. "Running it" means the build/test pipeline below.

**System prerequisites:** a `node` binary on `PATH` (real subprocess in tests).

**Environment:** none declared.

```
pip install -r requirements.txt
```

Test: `python3 -m pytest`

> **UNKNOWN** — some referenced build/regeneration tooling is not in a public clone — ask a maintainer for the contributor flow.

**Sibling repos:** some processes need a private sibling repo checked out alongside — ask a maintainer.

Operational processes require the private tier symlinks and manifest declared in `project.yaml` to be present before running automated tooling.
<!-- onboarding-surface:end run-it -->

<!-- onboarding-surface:begin pointers -->
- `spec/` — internal contracts
- `CLAUDE.md` — operating rules (and the best landmine source)
- `AGENTS.md` — operating rules (and the best landmine source)
- `GEMINI.md` — operating rules (and the best landmine source)
- `docs/` — deeper docs
- Some docs referenced internally are not in the public clone.
<!-- onboarding-surface:end pointers -->
