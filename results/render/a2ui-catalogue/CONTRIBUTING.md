# Contributing

<!-- onboarding-surface:begin first-contribution -->
Start with a scoped atom fix based on recent commit history, such as commit `f1c81ba5`: update candidate display components (`photo_grid` or `photo_stepper`) to handle missing imagery cleanly without showing a broken-image icon. Definition of done: verify in the renderer source that candidates lacking photo URLs do not render broken image containers, and confirm tests pass via `python3 -m pytest tests/ -q`.
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

Run `python3 -m pytest tests/ -q` prior to pushing. Note that tests explicitly audit `project.yaml` publication policies and staging flags (`test_project_manifest.py`, `test_staging.py`). If a deploy fails, verify whether the symptom is an unobservable deployment or a race condition on live surfaces using `worker-verify` and `gas-verify` rather than assuming code-level regression.
<!-- onboarding-surface:end verify -->
