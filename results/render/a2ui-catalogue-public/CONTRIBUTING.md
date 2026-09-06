# Contributing

<!-- onboarding-surface:begin first-contribution -->
Resolve parser parity between `scripts/parse_training_md.py` and Apps Script counterparts, or update atom definitions under `atoms/schema.yaml` marked as `stage: preview`. Run `python3 -m pytest tests/ -q` to confirm the manifest and staging audits pass without error.
<!-- onboarding-surface:end first-contribution -->

<!-- onboarding-surface:begin pr-gates -->
- CI must pass — `.github/workflows/`: build-apps.yml, deploy.yml, gemini-review.yml, release-renderer.yml.
- Commit-message convention: house style: commits carry a Co-Authored-By trailer; subjects end with a (#NN) PR reference.

Not found (so not required): CLA/DCO, a PR template.
<!-- onboarding-surface:end pr-gates -->

<!-- onboarding-surface:begin verify -->
```
python3 -m pytest
```

"Green" = 0 failures.

`node` must be on `PATH` — some tests shell out to it.

Running `python3 -m pytest tests/ -q` validates the project manifest and verifies that no staging-level preview atoms are leaked into published artifacts.
<!-- onboarding-surface:end verify -->
