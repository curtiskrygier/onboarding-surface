# Exposure demo — the 11 a2ui-catalogue landmines through `exposure: public`

Applies spec §15's `class` + `public` handling to the real landmines from
`ARCHITECTURE.md`. `ARCHITECTURE.md` itself is the `exposure: internal` rendering
(full candour — correct, because this worked example lives in a private repo).

| # (from ARCHITECTURE.md) | `class` | `public` rendering |
|---|---|---|
| 1 Deployed ≠ reachable (6 recorded instances) | `operational` | **keep, generalise:** "The characteristic failure here is a correct build that isn't live at the surface a user touches. After any deploy, run the matching `*-verify` process; treat 'pushed but not observable' as a deploy problem." *(drop the enumerated six)* |
| 2 Two failures on one symptom → STOP | `operational` | **keep verbatim** — it's a working practice, not a weakness |
| 3 Never track the private tier | `operational` + `private-ref` | **keep the rule**, it's a contributor instruction: "`ops/`, `**/Code.private.gs`, `.clasp.json` must stay untracked — the manifest audit fails otherwise." |
| 4 `public/` traces to `policy.published` | `operational` | **keep verbatim** |
| 5 Preview atoms repo-only | `operational` | **keep verbatim** |
| 6 Every operation via a declared process | `operational` | **keep verbatim** |
| 7 Renderer parity; `tools/list` change same commit | `operational` | **keep, soften:** drop "deadlocks the deploy that would resolve it" → "update the parity suite in the same commit or CI will block." |
| 8 `mcp:<verb>` hand-synced across two repos, **fails instantly and silently** | `exploitable` + `private-ref` | **pull from the public doc.** Emit to the maintainer-only report. Public gets at most: "Some cross-surface wiring is kept in sync by hand — check with a maintainer before adding a new action verb." No file names, no "silently". |
| 9 `requirements.txt` ↔ `deploy.yml` pip-list hand-sync (hit twice 2026-08-23) | `operational` | **keep, generalise:** "The CI workflow hardcodes its install list — add a new dependency to both." *(drop the date)* |
| 10 Commit/push via `ops.py`, unreachable from a public clone | `operational` + `clone_gap` | **keep:** "Committing/pushing here goes through `ops/ops.py`, which isn't in a public clone — ask a maintainer about the contribution flow from a fork." |
| 11 `a2uithoughts.md` is gitignored | `private-ref` + `clone_gap` | **minimise:** "Some design-rationale notes are not in the public clone." No filename, no "incident log". |

Also generalised in `public` mode outside the landmines list:

- **Codemap / dynamic-path** — replace "a Cloudflare Worker front over a
  standalone Apps Script backend; `mcp-worker/src/tools.js` in the private
  sibling" with "a thin edge front over a standalone backend."
- **`sibling_repos`** — "some maintenance processes need a private sibling repo
  checked out" rather than naming `a2ui-private` and its paths.

**Net:** of 11 landmines, `public` mode keeps 9 (7 verbatim, 2 generalised),
pulls 1 to a maintainer-only report, and minimises 1. Zero `exploitable` or
`private-ref` strings survive verbatim — the §13 "No over-exposure" check passes.
