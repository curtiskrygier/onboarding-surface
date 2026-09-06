# Contributing

<!-- onboarding-surface:begin first-contribution -->
Resolve minor display or fallback anomalies in atom renderers, such as the fix implemented in `photo_grid` and `photo_stepper` to avoid broken-image icons when candidate objects lack photos. Definition of done: verify that the atom schema accommodates missing image fields, execute `python3 -m pytest tests/ -q` to confirm the schema and staging checks pass, and verify through the appropriate parity test harness without directly modifying generated prompt files.
<!-- onboarding-surface:end first-contribution -->

<!-- onboarding-surface:begin pr-gates -->
- CI must pass — `.github/workflows/`: build-apps.yml, deploy.yml, gemini-review.yml, release-renderer.yml.

Not found (so not required): CLA/DCO, a commit convention, a PR template.
> **UNKNOWN** — branch-protection rules and required status checks are GitHub-only — not read offline
<!-- onboarding-surface:end pr-gates -->

<!-- onboarding-surface:begin verify -->
```
python3 -m pytest
```

"Green" = 0 failures.

`node` must be on `PATH` — some tests shell out to it.

Run `python3 -m pytest tests/ -q` before any push. This suite enforces manifest validation and staging policy: preview atoms (`stage: preview`) must not leak into publication pipelines, and publication boundaries defined in `project.yaml` must not be violated. A test failure in `test_project_manifest.py` or `test_staging.py` indicates an artifact has been exposed without opt-in or private tier files have been tracked.
<!-- onboarding-surface:end verify -->
