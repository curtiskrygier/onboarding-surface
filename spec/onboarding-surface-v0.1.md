# onboarding-surface — spec v0.1

**Status:** draft. This is the contract. The extraction code, the LLM prompt, the
parser, and the A2A wrapper all generate from or validate against it.

---

## 1. Purpose & principles

Produce the documentation a new contributor needs to reach a merged first PR,
and keep it true as the code changes.

1. **Never fabricate.** Every claim is mechanically derived and verifiable, or
   marked `authored, unverified`. A missing fact is stated as missing:
   `Verify: UNKNOWN — no test command found in package.json, Makefile, or CI`.
2. **Newcomer-first order** (inverted pyramid). What is this → how do I run it →
   where is everything → what will bite me → how do I contribute. Each section
   serves a smaller, more engaged reader.
3. **One Diátaxis mode per section.** Don't explain *why* inside the run-it
   steps; don't put a tutorial in the reference map.
4. **Deterministic sections are a formatter, not a gate** (see §7). CI rewrites
   them in place; it never fails a build on doc drift.
5. **Markdown is the product.** Three files, below. An interactive surface is
   out of scope for v0.1.

---

## 2. Outputs

| File | Reader | Sections (see §3) |
|---|---|---|
| `README.md` | someone deciding whether to use / try this | 1, 2, 3, 4, 10 |
| `ARCHITECTURE.md` | someone about to change code | 5, 6 |
| `CONTRIBUTING.md` | someone about to open a PR | 7, 8, 9 |

Each file carries generated blocks between `<!-- onboarding-surface:begin SECTION -->`
… `<!-- onboarding-surface:end SECTION -->` markers. Content outside markers is
hand-owned and never touched.

---

## 3. Section catalogue

`D` = deterministic (no LLM), `A` = authored (one governed LLM call), `H` = hybrid.
"Gap-flag" = when the source is absent, emit an explicit UNKNOWN, never a guess.

| # | Section | Diátaxis | File | Kind | Primary sources |
|---|---|---|---|---|---|
| 1 | What it is + who it's for | explanation | README | A | repo description, topics, existing README intro |
| 2 | Maturity signal | reference | README | D | last commit, tag cadence, CI status, open-issue age, archived flag |
| 3 | 60-second orientation + why it exists | explanation | README | A | existing docs, `docs/`, design notes, commit-message themes |
| 4 | Run it | tutorial | README | H | §4a below |
| 5 | The map (codemap + dynamic path) | reference | ARCHITECTURE.md | H | §5 below |
| 6 | The landmines (invariants, often as an absence) | explanation | ARCHITECTURE.md | H | §6 below — **history + lint configs, not the file tree** |
| 7 | First contribution | how-to | CONTRIBUTING.md | H | issue tracker query + a thin authored summary |
| 8 | Your PR will be rejected unless… | how-to | CONTRIBUTING.md | D | §8 below |
| 9 | Verify your change | how-to | CONTRIBUTING.md | H | test/lint commands from manifest + CI, gap-flagged |
| 10 | Pointers | reference | README | D | links to `docs/`, spec files, issue tracker, deploy runbook |

### 3.1 Section field shapes

Each generated section is emitted as both Markdown and a JSON record
(`{section, kind, diataxis, file, confidence, flags[], body_md, facts{}}`) so the
parser, the CI formatter, and the eval harness all read the same structure.
`confidence` ∈ `verified | inferred | unknown`. `flags` carries every UNKNOWN and
every `authored, unverified`.

---

## 4a. Run it — prerequisites & first-run state

The manifest gives the package-manager command. It does **not** give the things
that actually make first-run fail. Emit these as distinct subsections:

| Subsection | Deterministic anchors | Gap-flag when absent |
|---|---|---|
| System prerequisites | `.tool-versions`, `.nvmrc`, `engines` in package.json, `rust-toolchain.toml`, Dockerfile `FROM` + `apt-get`, devcontainer.json | "System packages: UNKNOWN — check with a maintainer" |
| Running services | `docker-compose.yml` / `compose.yaml` service list, `Procfile`, ports in config | "Requires external services: UNKNOWN" |
| Environment | `.env.example` / `.env.sample` keys (names only, never values), `config/` templates | "Required env vars: UNKNOWN — no .env.example" |
| First-run state | migration dirs (`migrations/`, `db/migrate/`), seed scripts, `Makefile`/`Taskfile`/`justfile` targets named `setup`/`bootstrap`/`init` | "DB/state setup: UNKNOWN" |
| The commands | install + run, from the above targets or manifest scripts | "Run command: UNKNOWN" |

Rule: list env var **names** only. Never read or echo a value from any `.env` file.

---

## 5. The map — codemap + dynamic path

Two parts, per matklad's static-vs-lifecycle distinction.

**Codemap (D + A).** A coarse module list — directory or top-level package
granularity, not files. For each: name, one-line "what it does" (A), and the
1–3 entities a newcomer would grep for (D, from exports / public symbols).
**No line-number links** — they rot. Point at symbol/grep search:
`` grep -r "class SketchExecutor" `` not `src/exec.py:214`.

**Dynamic path (A, anchored on D).** Where does a request / event / job *enter*
the system, what handles it, where does it persist. Anchors that are
deterministic: HTTP route registrations, queue consumers, CLI entrypoints, cron
definitions, the `main`/`handler` symbols. The narrative between them is authored.
Gap-flag if no entrypoint is detectable.

**Excluded:** implementation detail, anything "likely to change frequently",
per-function description.

---

## 6. The landmines — special handling

The highest-value section and the one an LLM gets **wrong** if fed only the file
tree: it cannot tell an intentional absence (an invariant) from an unbuilt
feature, and defaults to generic dogma maintainers reject
("controllers must never call repositories") even in a repo that does exactly
that on purpose.

**Inputs, in priority order:**

1. **Architectural-lint configs (D).** These are invariants already encoded:
   `dependency-cruiser`, `import-linter` (Python), `eslint-plugin-boundaries` /
   `eslint-plugin-import` rules, Go `internal/` packages, Rust `pub(crate)`
   visibility, ArchUnit tests, Nx/Turborepo project boundaries. Extract the rule,
   restate it plainly. `confidence: verified`.
2. **Revert commits + their messages (D→A).** `git log --grep=revert` and commits
   whose message contains "revert", "broke", "regression". The message often
   states the invariant. Summarise (A).
3. **Closed-PR review comments (D→A).** Comments matching `we don't`, `don't
   import`, `never call`, `breaks the`, `anti-pattern`, `has to stay`. Requires
   the platform API (GitHub/GitLab). Summarise (A).
4. **`CLAUDE.md` / `AGENTS.md` / `CONTRIBUTING.md` prose (A).** Repos that have
   these often state their landmines directly (e.g. "deployed ≠ reachable").

**If none of 1–4 are available:** the section is honestly short —
`Landmines: none extracted. Sources checked: lint configs, revert history,
review comments, agent docs.` Never pad with generic best practices.

Each landmine record: `{statement, source (lint|revert|review|doc), evidence_ref,
confidence}`.

---

## 7. First contribution

**Candidate issues (D).** Platform API query: label ∈ {`good first issue`,
`good-first-issue`, `help wanted`}, no assignee, updated within 90 days, low
comment count. Return the top 3–5.

**Per issue (A):** a one-paragraph "definition of done" derived from the issue
body + linked code. If the issue body is empty/vague, say so — don't invent scope.

**If zero candidates:** `No labelled starter issues. Smallest recent changes by
diff size: <list from git log --stat>` as a fallback surface of where small
contributions have landed.

---

## 8. Your PR will be rejected unless… (D)

Mechanical gates, from config only:

- CLA / DCO: `.github/workflows/*cla*`, DCO bot config, `Signed-off-by` in recent
  commits → "commits must be signed off (`git commit -s`)"
- Commit format: `commitlint.config.*`, `.czrc`, conventional-commits in recent
  history → the required prefix set
- PR template required fields: `.github/PULL_REQUEST_TEMPLATE*`
- Branch naming: branch-protection patterns, contributing prose
- Required checks: branch-protection required status checks (API) or CI job names

Each gate cites its source file. No source → not listed (not guessed).

---

## 9. Deterministic extraction — the fact base

One pass builds a `facts.json` before any LLM call:

```
repo:        name, description, topics, default_branch, archived, license
activity:    last_commit_at, commits_90d, tags[], tag_cadence_days, ci_status
structure:   tree (dirs + file counts), languages, entrypoints[], modules[]
run:         tool_versions{}, services[], env_var_names[], setup_targets[],
             install_cmd, run_cmd, test_cmd, lint_cmd     (any may be null)
invariants:  lint_boundary_rules[], go_internal_pkgs[], visibility_scopes[]
history:     revert_commits[], churn_by_dir{} (AST-filtered — exclude generated
             + bulk-reformat commits), review_comment_hits[]  (if API available)
contrib:     cla, dco, commit_convention, pr_template_fields[], branch_rules[],
             required_checks[]
issues:      starter_candidates[]   (if API available)
docs:        existing_readme_sections{}, has_architecture_md, has_contributing_md,
             agent_docs[]  (CLAUDE.md / AGENTS.md), doc_dirs[]
```

Anything `null` in `facts.json` becomes a gap-flag in the surface, never a
prompt for the LLM to fill.

---

## 10. Authored generation — the single governed call

One LLM call. Input: `facts.json` + this spec's section schema + the rules below.
Output: the authored/hybrid section bodies as the JSON records from §3.1.

Rules given to the model:

- Write only from `facts.json`. If a fact needed for a sentence is `null`, emit
  the section's gap-flag string and move on. Do not reason about what the value
  "probably" is.
- One Diátaxis mode per section (stated per section).
- No line-number links. Reference code by symbol name for grep.
- Landmines: only from `facts.invariants` + `facts.history`. If both are empty,
  the section is the "none extracted" string.
- No generic software-engineering advice anywhere. Every sentence is about *this*
  repo.
- British English, plain language, short sentences (non-native readers).

Then a deterministic parse validates the records against §3.1 and the marker
structure before anything is written.

---

## 11. CI integration — formatter, not gate

- **Every push, doc-relevant paths changed:** regenerate the **deterministic**
  sections, write them between their markers, and **amend into the same push**
  (like `prettier --write` in CI). No failing check. If the runner can't push
  (fork PR), post the diff as a review comment instead.
- **Merge to main / `docs:refresh` label / weekly cron:** run the authored call
  too; open **one** PR with the combined update. Never one PR per merge.
- **Never** a required status check on doc content.

"doc-relevant paths" = a configurable glob: manifests, CI config, `docs/`,
lint configs, `.github/`, `ARCHITECTURE.md`, top-level source dirs. Not every typo.

---

## 12. A2A interface — **built 2026-09-06** (`serve/`, full shape in `docs/design.md`)

**Revised from the original sketch below** (kept struck-through-in-spirit for
the record): that design had the server run `extract` itself over a caller-
bundled raw file slice. `extract` as actually built is a `git`-checkout tool —
reimplementing it against an uploaded bundle would duplicate that logic for a
shakier input, and (Gemini 3.8 Flash design review, 2026-09-06) reopens the
security surface a stateless, repo-blind server was meant to avoid. As built:

- `GET /.well-known/agent-card.json` — four skills: `author`, `render`,
  `draw`, `full` (chains all three). Split rather than one `mode=check|full`
  call — batching two LLM steps into one sync HTTP round trip is fragile
  under proxy/client timeouts (60–90s for `full`); a caller who hasn't sized
  their own timeouts for that should call the individual skills instead.
- `POST /` — `message/send`. One `DataPart`: `{job, facts, digest?, authored?,
  exposure?, model?, detail?}` in; one `DataPart` reply: `{docs?, authored?,
  sketch_svg?}` out. Stateless — no Task lifecycle, no memory between calls.
- **The caller runs `extract` locally** (already its whole contract — needs
  `git`) and sends the resulting `facts.json`, plus an optional
  `author.build_digest()` string for the `author`/`full` skills. The server
  never clones, never reads a caller's filesystem, never sees credentials.
- `render` always runs `--fresh` server-side — there's no target repo here to
  splice into; splicing is trivially the caller's own job.
- Auth: a static bearer token (`ONBOARDING_SURFACE_TOKEN`, no-op when unset)
  — proportionate for a solo repo per the same review; OAuth/OIDC and rate
  limiting explicitly deferred. A 512 KB payload cap rejects an oversized
  request before it's parsed.

Verified in-process (`serve/test_serve.py`, real `a2a-sdk` client + server,
`httpx.ASGITransport`): `render` and `draw` round-trip correctly, the public
exposure filter holds identically to the CLI, error paths (missing `facts`,
oversized payload, no auth) reply cleanly. `author`/`full` verified manually
(real API cost) against `a2ui-catalogue`'s real facts — public exposure held
end to end from a single A2A call.

**Original v0.1 sketch, superseded above:** `GET /.well-known/agent-card.json`
— skill `generate-onboarding-surface` (returns all three files + `facts.json`
+ report); input modes: file parts (the doc-relevant repo slice) + a `mode`
text part (`check` = deterministic only, `full` = + authored). `POST /` —
`message/send`, repo slice in, surface out. Auth: bearer token or Google OIDC
(for GitHub Actions with WIF).

---

## 13. Validation / eval rubric

Per generated surface, on a held-out set of repos:

| Check | Pass condition |
|---|---|
| No fabrication | zero invented commands/paths/entities (spot-check against repo) |
| Gaps honest | every `null` fact surfaces as an explicit UNKNOWN |
| Run it works | a fresh clone + the documented steps reaches "it's up" (or the gap-flags correctly predicted the missing piece) |
| Map is findable | every named entity resolves via the suggested grep |
| Landmines real | each landmine traces to a lint rule / revert / review comment; zero generic dogma |
| Diátaxis clean | no section mixes modes (blind judge) |
| Contributor judge | a dev unfamiliar with the repo rates "could I make a first PR from this" 0–2 |

---

## 14. v0.1 scope boundaries

**In:** the three Markdown files; deterministic extraction; one authored call;
the CI formatter; a GitHub-only platform adapter (issues, review comments,
branch protection).

**Out:** the interactive A2UI surface; the "document that learns" analytics;
GitLab/Bitbucket adapters; KB/SOP source adapter (that's the second input into
the same schema, later); multi-repo / monorepo-package granularity.

**Open questions:**

- Codemap granularity for monorepos — per-package or per-app? (deferred, monorepo out for v0.1)
- Review-comment mining needs the GitHub API with `pull-requests: read` — acceptable scope for a CI token?
- Where authored-section staleness is reported when there's no `docs:refresh` cadence — a `docs-health.json` artifact vs a scheduled issue.

---

## 15. Confirmed v0.2 changes (from the a2ui-catalogue pressure-test)

**New deterministic facts** (extractor produces them; each prevents a quietly
wrong surface):

- `facts.clone_gaps[]` — paths referenced in docs but gitignored / absent from a
  fresh clone. Every section that leans on one must gap-flag. (a2ui-catalogue:
  `ops/`, `a2uithoughts.md` — its whole documented workflow is invisible to the
  actual audience.)
- `facts.repo_kind` — `service | library | toolkit | monorepo | docs`. Shapes the
  "Run it" section: a toolkit with no server shouldn't read as a pile of UNKNOWNs.
- `facts.sibling_repos[]` — cross-repo checkout dependencies ("needs `../x` for Y").

**New landmines source** (§6): **config-file prose** — comments in CI yml,
Makefiles, `.tool-versions`, `requirements.txt`. (a2ui-catalogue's
`requirements.txt` ↔ `deploy.yml` hand-sync landmine came from exactly there.)

**`exposure` mode + landmine classification.** An honest onboarding surface
over-shares if unguarded — it amplifies buried `CLAUDE.md` candour into a
front-and-centre `ARCHITECTURE.md`, names private infra, and catalogues
fragility a competitor or adopter reads very differently than a contributor.

- `exposure: internal` (default when output lands in a private repo / gated docs)
  — full candour.
- `exposure: public` — landmines **generalised** (no private-repo names, no
  credential paths, no gitignored-file pointers); a "cross-repo config pair is
  hand-synced — ask a maintainer" instead of naming the two files.

**Enforced by classification + a deterministic render filter, not by the prompt
alone.** The prompt tells `author` to generalise; the render step then *proves*
it. `author` returns `landmines` as a JSON array of records `{statement, source,
class}`:

| `class` | `public` handling |
|---|---|
| `operational` — fragility the team already knows ("deploy ≠ reachable") | kept, written already-generalised |
| `exploitable` — "fails silently", "can be bypassed", "no guard" | **dropped from the doc** — moved to `MAINTAINER-NOTES.md` |
| `private-ref` — names a private repo / credential path / hidden tier | **dropped from the doc** — moved to `MAINTAINER-NOTES.md` |

`render --exposure public` then:

1. **Filters** — keeps only `operational` records in the `landmines` block; the
   rest go to a `MAINTAINER-NOTES.md` sibling file (never written into the repo
   docs), with a **non-quantified** footnote ("some maintainer-only notes … kept
   out of the public docs" — no count, no class names: a "3 held back" line
   advertises what to go looking for).
2. **Safety net** — any record the model called `operational` whose statement
   still names a `clone_gaps` path, a `sibling_repos` name, or a known
   credential/private token is force-reclassified to `private-ref` before the
   filter runs. A stale hand-written `authored.json` (legacy string landmines,
   all `operational`) is caught here too.
3. **Leak scan** — authored *prose* sections (`what-it-is`, `orientation`,
   `run-it`, `first-contribution`, `codemap`) are scanned for the same private
   tokens; residual hits are **reported** to `MAINTAINER-NOTES.md` (flagged for a
   human, never machine-rewritten — string redaction was tried and reverted as
   too fragile).

**Deterministic sections are filtered in `render` directly — they never reach
the model:**

- `pointers`, `run-it` machine parts, the sibling-repo line → generalised
  wording, no private names.
- `run-it` build/regen `clone_gaps` → a gap that is **purely private tooling**
  (matches `_PRIVATE_HINT`) is **omitted entirely** from the public section — no
  `> **UNKNOWN**` caveat announcing a hidden flow — and noted in
  `MAINTAINER-NOTES.md`. A non-private buildable gap is still named for the
  contributor.
- `codemap` (authored) → a **whole markdown table row** whose cells name a
  private token is dropped in `public` mode (row-level, not char-level) and
  noted. Row deletion is structured; it is not the prose mangling that was
  reverted.

`MAINTAINER-NOTES.md` is surfaced in the HITL `review` page under "Held back from
the public surface".

Add to §13 rubric: **No over-exposure** — in `public` mode, zero `exploitable`
or `private-ref` landmines appear verbatim in the docs; every held record and
every residual prose leak is accounted for in `MAINTAINER-NOTES.md`.

## 16. Visuals (v0.2 — §16b + §16c built 2026-09-06, §16a deferred)

Two kinds of picture, two sources. Keep them separate.

### 16a. Deterministic diagrams — Mermaid *(deferred)*

A module graph from `facts.json` as Mermaid was prototyped and pulled: with
only `facts.structure.modules` available it's nodes-only, and a flowchart with
no edges doesn't earn its space. Revisit once the extractor does import/
dependency analysis and the graph can show real relationships.

### 16b. Illustrative sketch — D2, deterministic — **built**

**`draw/` (2026-09-06, revised same day).** `facts.json` → `build_diagram_spec()`
(box/edge/zone list, from facts only) → `build_d2_source()` (deterministic
translation to [D2](https://d2lang.com) syntax) → the `d2` CLI → a cached SVG.
**No LLM call in this path at all** — as deterministic as `render` itself.

```
python3 -m draw architecture facts.json     # -> <repo>/assets/onboarding/architecture-sketch.svg
python3 -m draw architecture facts.json --exposure public --detail detailed --out p.svg
```

**Superseded design, kept for the record:** the original build called a
`freeform_canvas`-shaped LLM one-shot to draw the SVG freehand — the model
guessing box positions itself. Curtis, on comparing the result to the original
hand-tuned test: "did not look as professional... revisit the prompt, including
graphic size." A prompt can be tuned indefinitely; a model laying out
coordinates by hand will never match a real layout engine. **D2 does the
layout deterministically from the identical spec** — no prompt to maintain, no
canvas-size guessing (D2 sizes the SVG to its own content), no chance of an
invented relationship. `examples/a2ui-catalogue/architecture-sketch.svg` (the
very first hand-tuned test, 800×520, cramped) and the intermediate
freeform_canvas pass both stay in the repo as the record of why this landed
where it did.

Not in `extract`/`render`'s call chain — cadence-only (`onboard.py --art`, or
run directly). `render.sec_codemap` already knew how to embed the result
(checks `<repo>/assets/onboarding/architecture-sketch.svg`, or an authored
`_has_sketch` flag) — no `render` change was needed.

**Honesty.** `build_diagram_spec()` builds boxes/edges from
`facts.structure.modules`, `facts.structure.entrypoints`, `facts.run.services`,
`facts.activity.ci_present` + `generated_file_count`, `facts.clone_gaps`/
`sibling_repos` — nothing else, and `build_d2_source()` is a pure syntax
translation of that spec, no content decisions. Since §16a is deferred (no
import-graph analysis), the only edges drawn are the ones facts actually
prove: containment (repo → its modules), an entrypoint starting the repo, CI
producing a declared generated-output dir, a contributor needing a declared
sibling repo or private path — never an inferred dependency.

**Representativeness bug, found and fixed 2026-09-06.** Curtis, on the first
real D2 render: "not sure the diagram properly represented the codebase - bit
gas heavy, no web, mcp apps etc." Two real bugs, not a D2 problem:
1. `extract`'s own `modules` list had drifted from `_LANG`'s extension set
   (missing `.mjs`/`.tsx`/`.jsx`/`.cjs`/`.kt`/`.c`/`.cpp`) — a2ui-catalogue's
   real MCP surface (`mcp/`, all `.mjs`) was invisible to `modules` entirely,
   not just deprioritised. Fixed, and while there: a directory entirely inside
   a `_GENERATED_DIR` (`public/`) could still qualify as a "module" via one
   stray vendored file with a code extension nested inside it — `public/`
   (1201 generated files) was ranking as the #1 "module" once size-ranking
   replaced alphabetising (next bug). Both fixed together in `structure_facts`.
2. `modules` was sorted alphabetically for storage, throwing away the real
   file-count ranking `dir_counts.most_common()` had already computed —
   whatever truncates this list (this diagram's box budget, `render`'s codemap
   table) was effectively picking the first N alphabetically, not the N most
   substantial. Fixed: `modules` now stays ranked by real (non-generated) file
   count.
3. Even with real ranking, generic scaffolding (`tests/`, `scripts/`,
   `knowledge-catalogue/`) still outranks small-but-real product surfaces by
   raw file count. `draw._rank_modules()` reorders (doesn't drop) modules
   matching a generic-name pattern (tests/scripts/examples/docs/spec/vendors/
   benchmarks/etc.) behind everything else, so product code wins the limited
   box budget. Verified: a2ui-catalogue's diagram now shows `apps-script-surface`,
   `renderers`, `components`, `mcp`, `a2a_counterpart`, `cloud-run-renderer` —
   not `tests`/`scripts`/`knowledge-catalogue`.

**Exposure (§15) inherits at the spec-building step**, before any rendering
happens — reuses `render.render`'s own `_private_tokens`/`_hits_private` to
generalise a box label (e.g. `ops.py` → "a private/internal path"). Verified:
internal names the real path; public doesn't; nothing else in the diagram
differs.

**Cache:** `<out>.svg` + `<out>.inputhash` side by side; an unchanged
structured input is a no-op; `--force` bypasses it.

**Style:** D2 theme 0 ("Neutral Default") — Curtis's pick, compared side by
side against Cool Classics and hand-drawn sketch mode on the same diagram.

**Verified 2026-09-06** (`a2ui-catalogue`, both exposures, after both the D2
switch and the representativeness fix): one `d2` compile each (~350ms, no
network), viewBox auto-sized to content (`0 0 1366 672` for this repo's real
box count — no more picking a canvas size and hoping it fits), all labels
traced directly back to the spec, no dead space, zones as real D2 containers.
Also verified on `maison` and `onboarding-surface` itself (small/degenerate
box counts) — both render cleanly.

**Pipeline placement — as built:**

- Cadence-only by convention — `onboard.py --art` (or `python3 -m draw
  architecture` directly), never wired into `extract`/`render`'s own call
  chain, never per-push, never gated. (No longer LLM-driven, so nothing here
  strictly *requires* cadence-only for cost/latency reasons — kept anyway so a
  repo's diagram doesn't churn on every commit.)
- Spec built from `facts.json` in `draw.build_diagram_spec()`; D2 source built
  in `draw.build_d2_source()` — both deterministic code, no model involved.
- Cache: `<out>.svg` + `<out>.inputhash`; unchanged input → no-op; `--force`
  bypasses it.
- Exposure inherits (§15) at spec-build time: a box that would carry a
  `private-ref` label is generalised before D2 source is even built.
- Requires the `d2` CLI on `PATH` (`d2lang.com`) — `render_d2()` raises a clear
  `D2Error` if it's missing, never a bare `FileNotFoundError`.

**Where it lands:**

- **`ARCHITECTURE.md`, not `README.md`.** A marketing README's visual should
  be a product shot (the rendered UI the tool produces), not an internal
  diagram — those read as "enterprise vendor" on a landing page.
  `ARCHITECTURE.md` is the reader who wants it: someone about to change code.
  `render.sec_codemap` embeds it at the top of the codemap section, above the
  module table.
- The sketch's labels pass the same `public` / `internal` exposure filter
  (§15) as the prose.
- v2 interactive A2UI surface: an `agent_sketchpad` atom pre-loaded with the SVG.

### 16c. Repo mark — the draw agent (freeform_canvas) — **built**

**`draw/` (2026-09-06).** When a repo has **no existing mark**
(`draw.has_existing_mark()`: no `assets/logo*`/`assets/favicon*`, no `.github/`
brand asset, no logo/wordmark/brand image referenced in the README), the agent
can *propose* a minimal geometric mark.

```
python3 -m draw mark facts.json --n 3            # -> <repo>/assets/onboarding/mark-candidates/
python3 -m draw adopt-mark mark-2.svg --repo <repo>   # the ONLY step that writes into the repo
```

**How it differs from 16b, and why it still needs a human (unlike 16b, which
no longer does):** 16b lays out *known* boxes from `facts.json` — that's why
D2, a real layout engine with no creative decisions to make, was the right
fix. 16c *invents a metaphor* — the shakiest thing a one-shot generator does,
confirmed live 2026-09-06 for `onboarding-surface` itself: two concepts, one
read as "a chromosome", one landed. There's no deterministic substitute for
"invent a visual idea", so this path stays LLM-driven and human-gated.

- **A proposal artifact, never auto-adopted.** `propose_marks()` generates
  **N candidates** (default 3) in one call, each a genuinely distinct visual
  metaphor (not colour/shape variations of one idea) — writes them to a
  `mark-candidates/` dir with a `manifest.json` (concept + justification per
  candidate) and stops. Nothing writes into the repo's own `assets/` except
  `adopt_mark()`, a separate, explicit, human-invoked step. Not in the CI loop
  — a logo has a one-time lifecycle, not a cadence.
- **Guarded by `has_existing_mark()`** — refuses to propose (needs `--force`)
  when the repo already has a mark. Verified: correctly refuses on
  a2ui-catalogue (README wordmark image) and onboarding-surface itself
  (`assets/logo.svg`); correctly proceeds on `maison` (no mark).
- **Exposure (§15) doesn't apply** — an abstract mark carries no `private-ref`
  risk. `build_mark_seed()` still only uses real `facts.repo` fields (name,
  description, topics, `repo_kind`) — no invention on the input side either.

**Prompt:** minimal-geometric-mark constraints (`viewBox 0 0 240 240`,
transparent, ≤ 5 shapes, one accent colour, NO TEXT, flat, centred, generous
margin) + the concept seed. Higher temperature (0.9) than 16b's old prompt
(0.4) — here variety across candidates is the point, not fidelity to a fixed
input.

**Post-processing (`postprocess_mark()`, shares `sanitise_svg()`'s dangerous-tag
stripping with 16b's old path).** Raw draw output needs SVG surgery before it's
usable:

1. strip the baked background rect (`_strip_full_canvas_bg_rect()` — sized to
   the SVG's own viewBox, not hardcoded, so it works for both 16b's old fixed
   canvas and 16c's tight one)
2. tighten `viewBox` to the artwork's real bounding box + even padding (~24
   units) — `_svg_bbox()` is attribute-aware (rect/circle/ellipse/line/
   polyline/polygon/path), not a blind number scan
3. drop redundant attrs (`ry` alongside an equal `rx`, `width`/`height` on the
   root once `viewBox` is set)
4. emit a `currentColor` monochrome variant alongside the colour one
   (`to_monochrome()`) — verified: every real fill/stroke colour swapped,
   `none`/`transparent` left alone

**Verified 2026-09-06** (`maison`, no existing mark): one call, 3 candidates
("Gabled Keystone Arch", "Isometric Spatial Cube", "Sheltered Core" — genuinely
distinct metaphors, all house-themed per the real concept seed), each
post-processed cleanly (tight viewBox, no root width/height, mono variant
correct), `adopt-mark` verified writing `logo.svg` + `favicon.svg` +
`logo-mono.svg` into a target repo's `assets/`.

**Where it lands (on a pick):** `assets/logo.svg` + `assets/favicon.svg` +
`assets/logo-mono.svg`; a modest `<img … width="56–64">` above the README
title; available for a wordmark lockup. Never a hero.

### 16d. Both visual jobs are A2A delegations (16c today; 16b once `serve` exists)

16c is the onboarding-surface agent calling the **draw agent** over A2A — a
specialist it doesn't reimplement, exactly as designed. 16b no longer calls an
LLM at all (D2, deterministic), so it isn't a draw-agent delegation any more —
it's local orchestration of a real diagram-layout tool, the same class of work
as `render` itself. Still a candidate for its own two-agent flow in the
`agentic-battle-testing` Agents inventory. The governed prose call (§10) is the
third delegation. The onboarding-surface agent's own job is deterministic
extraction + orchestration + post-processing; it draws nothing and writes no
prose itself.
