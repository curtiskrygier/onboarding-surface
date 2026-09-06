<!-- Worked example per spec v0.1 §5–6. Hand-authored. -->

# Architecture

## The map

<!-- onboarding-surface:begin codemap -->
Coarse — where things live, and the entity to grep for. No line links.

| Area | What it does | Grep for |
|---|---|---|
| `atoms/schema.yaml` | **The source of truth.** Every atom: type, fields, surfaces, stage. | `- type:` |
| `scripts/gen_*.py` | Generators. Each reads `schema.yaml` (or the compiled `public/spec.json`) and writes one artifact. ~20 of them. | `def main` in `scripts/gen_public_catalog.py` |
| `renderers/a2ui_v1.py` | The **Python reference renderer** for A2UI v1.0 messages. | `class`/`def render` |
| `apps-script-surface/gas-wired-renderer/` | The Apps Script renderer + `A2UIState.html`. `_a2uiActionTransport` in that file has the `http` transport branch (wired dialect over plain POST, not `google.script.run`). | `_a2uiActionTransport` |
| `mcp/` | The `@a2ui/mcp` npm package. Bundles a catalogue snapshot from `mcp/data/` so it runs standalone. | `mcp/scripts/sync-data.mjs` |
| `ops/` | **Private tier — not in a public clone.** `ops.py` (the declared-process runner) + `project-ops.yaml` (78 processes) + credentials. | — |
| `project.yaml` | The public inventory: `policy`, `generators`, `staging`. Read before operating. | `generators:` |
| `public/` | **Generated output.** Deployed to `a2uicatalog.ai`. Most-churned path in the repo by far. Every file must trace to a `policy.published` rule (`tests/test_project_manifest.py`). | — |
| `tests/` | ~741. The invariant-enforcing ones: `test_project_manifest.py`, `test_staging.py`, `test_parser_parity.py`. | — |
| `a2a_counterpart/`, `cloud-run-renderer/`, `googlechat/` | Per-surface adapters / deployables. | — |
<!-- onboarding-surface:end codemap -->

## The dynamic path

<!-- onboarding-surface:begin dynamic-path -->
**Authoring a change:** edit `atoms/schema.yaml` → run the generators → they
rewrite `public/`, the JSON schemas, the compat matrix in `README.md` (between
markers), the MCP bundle → tests re-verify → CI deploys `public/` and the
renderers on merge to `main`.

**At runtime:** an agent calls the MCP endpoint (`a2uicatalog.ai/mcp` — a
Cloudflare Worker front over a standalone Apps Script backend) → gets the atom
vocabulary → emits an A2UI payload → a renderer (`a2ui_v1.py` / the `.gs` port /
the MCP-Apps bundle / the Slack mapping) turns it into markup for the target
surface.
<!-- onboarding-surface:end dynamic-path -->

## The landmines

<!-- onboarding-surface:begin landmines -->
Sourced from `CLAUDE.md`, `requirements.txt`'s own header, `ops/project-ops.yaml`
process notes, and the invariant tests. Each is a real thing that has bitten
this repo.

1. **Deployed ≠ reachable.** The characteristic failure here is a *correct* build
   that never became true at the surface a user touches — six recorded
   instances (template cache, lost deploy race, clasp identity clobber, stale
   Worker bundle, a parity gate blocking its own fix, an undiscoverable
   capability). A change that's committed and pushed but not observable live is
   a *deploy* problem until proven otherwise. After any deploy, run the matching
   `*-verify` process. *(source: CLAUDE.md)*

2. **Two failures on the same symptom → STOP.** Report what you observed, what
   you ruled out, what you need. Do not attempt a third fix. *(CLAUDE.md,
   adapted from `ops/improve.yaml`)*

3. **Never track the private tier.** `ops/`, `**/Code.private.gs`, `.clasp.json`
   must stay untracked — the manifest audit *fails the build* if they appear.
   *(CLAUDE.md; `check_tracked_deps.py`)*

4. **Everything under `public/` must trace to a `policy.published` rule** in
   `project.yaml`. Generators write there; publication is opt-in per artifact.
   *(`tests/test_project_manifest.py`)*

5. **Preview atoms are repo-only.** `stage: preview` in `schema.yaml` → every
   publication pipeline filters it out. New dev-first atoms start as preview.
   *(`tests/test_staging.py`)*

6. **Every operation goes through a declared process** (`ops.py run <x>`).
   Improvised `clasp push` / `clasp deploy` / ad-hoc regeneration chains are the
   exact failure mode the system exists to prevent. *(CLAUDE.md)*

7. **Renderer parity.** `renderers/a2ui_v1.py` is the reference; its `.gs` / `.html`
   mirrors must stay deep-equal (parity harness in pytest). Any deliberate
   `tools/list` change needs the parity suite updated *in the same commit*, or
   the gate deadlocks the deploy that would resolve it. *(CLAUDE.md;
   `test_parser_parity.py`)*

8. **`mcp:<verb>` is hand-synced across two repos.** `mcp-worker/src/tools.js`
   (private sibling) and `A2UIState.html`'s `MCP_VERBS` map. A verb in one but
   not the other fails *instantly and silently* — a click that does nothing.
   *(CLAUDE.md)*

9. **`requirements.txt` and `.github/workflows/deploy.yml`'s pip list are
   hand-synced.** The workflow hardcodes its install list. A dep added only to
   `requirements.txt` is the drift class this estate hit twice on 2026-08-23.
   *(requirements.txt header)*

10. **Commit via `python3 ops/ops.py commit "<msg>"`** (sync-window time
    stamping), not raw `git commit`. Push via `ops.py run repo-publish` — gated
    by `pre_push_audit.py` + `check_tracked_deps.py`. *(CLAUDE.md)* — and this
    itself is unreachable from a public clone (landmine 3).

11. **`a2uithoughts.md` is gitignored.** The design rationale and incident log
    that explains *why* half these rules exist is not in a clone.
<!-- onboarding-surface:end landmines -->
