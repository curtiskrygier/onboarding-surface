<!-- Worked example per spec v0.1 §7–9. Hand-authored. -->

# Contributing

## First contribution

<!-- onboarding-surface:begin first-contribution -->
Starter issues: labels **`good first issue`** and **`help wanted`** exist on the
tracker. At extraction time no open issue carried either label — check
[the tracker](https://github.com/a2uicatalog/a2ui/issues) directly.

Fallback — where small changes have recently landed (by diff size): new atoms in
`atoms/schema.yaml` + their renderer registration, generator link/label fixes,
and per-surface adapter tweaks under `apps-script-surface/` and `googlechat/`.

A well-scoped first change here: **add or fix one atom**. It touches one
`schema.yaml` entry, its renderer(s), a generated snapshot, and a test — a real
slice of the system with a bounded blast radius. Definition of done: `schema.yaml`
updated, generators re-run, `pytest tests/ -q` green, the atom renders on its
declared surfaces.
<!-- onboarding-surface:end first-contribution -->

## Your PR will be rejected unless…

<!-- onboarding-surface:begin pr-gates -->
Mechanical gates found in config:

- **CI must pass** — `.github/workflows/`: `build-apps`, `deploy`,
  `release-renderer`, plus `gemini-review` (an automated PR review posts
  comments; it does not block, but expect them).
- **No private-tier files staged** — `ops/`, `**/Code.private.gs`, `.clasp.json`.
  The manifest audit fails otherwise.
- **`public/` additions must be declared** — a new file under `public/` needs a
  matching entry in `project.yaml` `policy.published`, or `test_project_manifest.py`
  fails.
- **Schema change → regenerate** — if you touch `atoms/schema.yaml` without
  re-running the generators, the generated snapshots (compat matrix in
  `README.md`, `public/spec.json`, JSON schemas) go stale and their tests fail.

Not found (so not required): no `CONTRIBUTING` existed before this, no PR
template, no CLA/DCO, no commit-message convention config. Recent history uses
`Co-Authored-By:` trailers and a `#NN`-style PR reference in the subject.
<!-- onboarding-surface:end pr-gates -->

## Verify your change

<!-- onboarding-surface:begin verify -->
```
python3 -m pytest tests/ -q
```
~741 tests, ~2.5 min. "Green" = 0 failures (2 skips are expected). The
invariant tests worth knowing you tripped: `test_project_manifest.py` (public/
tracing), `test_staging.py` (preview atoms not leaked), `test_parser_parity.py`
(Python renderer vs its `.gs`/`.html` mirrors).

`node` must be on `PATH` — ~9 tests shell out to it for the compiled JS bundle;
without it they error rather than skip.

Regenerating derived artifacts to check they still build: **UNKNOWN from a public
clone** — the `ops.py run catalog-rebuild` path documented in `CLAUDE.md` needs
the private `ops/` tier. Running the `scripts/gen_*.py` individually is the
likely substitute; confirm order with a maintainer.
<!-- onboarding-surface:end verify -->
