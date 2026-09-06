# Contributing

<!-- onboarding-surface:begin first-contribution -->
Starter issues carry `good first issue` / `help wanted` — check the tracker. A well-scoped first change: **add or fix one atom** — one `schema.yaml` entry, its renderer, a generated snapshot, a test. Definition of done: `schema.yaml` updated, generators re-run, `pytest tests/ -q` green, the atom renders on its declared surfaces.
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

The invariant tests worth knowing you tripped: `test_project_manifest.py` (public/ tracing), `test_staging.py` (preview atoms not leaked), `test_parser_parity.py` (renderer vs its mirrors).
<!-- onboarding-surface:end verify -->
