# Architecture

<!-- onboarding-surface:begin codemap -->
| area | what it does | grep for |
|---|---|---|
| `atoms/schema.yaml` | the source of truth — every atom's type, fields, surfaces, stage | `- type:` |
| `scripts/gen_*.py` | generators; each reads `schema.yaml` and writes one artifact | `def main` |
| `renderers/a2ui_v1.py` | the Python reference renderer; `.gs`/`.html` mirrors stay deep-equal | `def render` |
| `ops/` | **private tier — not in a public clone.** `ops.py` + `project.yaml` (78 processes) | — |
| `public/` | generated output, deployed to a2uicatalog.ai; every file traces to a `policy.published` rule | — |
<!-- onboarding-surface:end codemap -->

<!-- onboarding-surface:begin landmines -->
- **Deployed ≠ reachable.** The characteristic failure is a correct build that isn't live at the surface a user touches (six recorded). After any deploy, run the matching `*-verify` process. *(source: CLAUDE.md)*
- **Two failures on one symptom → STOP.** Report what you observed / ruled out / need. *(source: CLAUDE.md)*
- **Never track the private tier** — `ops/`, `**/Code.private.gs`, `.clasp.json`; the manifest audit fails otherwise. *(source: CLAUDE.md)*
- **Commit via `python3 ops/ops.py commit`** (sync-window stamping), push via `ops.py run repo-publish` — and both are unreachable from a public clone. *(source: authored)*
<!-- onboarding-surface:end landmines -->
