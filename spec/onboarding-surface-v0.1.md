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

## 12. A2A interface (summary — full shape in `docs/design.md`)

- `GET /.well-known/agent-card.json` — skills: `generate-onboarding-surface`
  (returns all three files + `facts.json` + report). Input modes: file parts
  (the doc-relevant repo slice) + a `mode` text part (`check` = deterministic
  only, `full` = + authored).
- `POST /` — `message/send`. Stateless: repo slice in, surface out.
- Auth: bearer token or Google OIDC (for GitHub Actions with WIF).

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

Every landmine record gets a `class`:

| `class` | `public` handling |
|---|---|
| `operational` — fragility the team already knows ("deploy ≠ reachable") | generalise, keep |
| `exploitable` — "fails silently", "can be bypassed", "no guard" | **never public-verbatim** — emit to a separate maintainer-only report |
| `private-ref` — names a private repo / credential path / hidden tier | strip or generalise |

Add to §13 rubric: **No over-exposure** — in `public` mode, zero `exploitable`
or `private-ref` landmines appear verbatim.

## 16. Visuals (v0.2 candidate — tested 2026-09-06)

Two kinds of picture, two sources. Keep them separate.

### 16a. Deterministic diagrams — Mermaid

A module graph and the dynamic path (entry → handler → store), emitted as
**Mermaid** from `facts.json`. GitHub renders it inline; it regenerates on the
CI-formatter cadence like any other deterministic block. This is the *reliable*
picture — the one that has to be exact.

### 16b. Illustrative sketch — the draw agent (freeform_canvas, one-shot)

An architecture sketch and/or a hero visual via the **draw agent**, using the
**non-progressive `freeform_canvas` path** (`generate_diagram_payload(prompt,
mode="svg")`), not the streaming `/a2a/sketch` stroke path — one structured LLM
call, returns a finished sanitised SVG string, passes the atom's own validator.

**Tested 2026-09-06** on a2ui-catalogue's real codemap facts, `gemini-3.8-flash`:
one call, ~6 KB SVG, `render_diagram_response` → `accepted: True`; 10 boxes, 10
connectors, all labels verbatim from the facts, correct two-zone layout (build
flow top-to-bottom, runtime flow left-to-right). **Usable, but cramped** — 800×520
for 10 boxes, 10.5px text, zones not visually separated, dead space between them.
Artifact: `examples/a2ui-catalogue/architecture-sketch.svg`.

**Prompt guidance** (the draw agent gets this, built by onboarding-surface):

- **Structured input, not prose.** Pass the box list, edge list (with relation
  labels), and zone grouping from `facts.json`. The model does *layout*; it does
  not invent content. This also keeps the exposure filter (§15) clean — the label
  strings are yours.
- **Generous canvas:** `viewBox 0 0 1100 700`, boxes ≥ 160×64, text ≥ 12px. A box
  needing >3 lines gets bigger, not smaller text.
- **Zones:** each distinct flow in its own horizontal band with a faint
  background rect + a band title; clear whitespace between bands; bridge them with
  a labelled connector (no dead space).
- **Direction per zone:** build/author flows top→bottom, runtime/request flows
  left→right.
- **Label the arrows** where the relation isn't obvious ("generates", "deployed
  by CI", "emits").
- **Detail knob:** `overview` (≤10 boxes, the shape — default) or `detailed`
  (expand key nodes: renderer variants, generated artifacts, CI, private tier —
  use for ARCHITECTURE.md).
- One accent colour for the entry node; legend only if >2 fills.

**Pipeline placement:**

- An `authored` artifact — LLM output, non-deterministic. Cadence only
  (merge / label / cron), never per-push, never gated. `mode=check` / `mode=full`
  don't call it; a `render_art` flag does.
- **Prompt built from `facts.json`** — the codemap modules + dynamic path. The
  facts drive both the Mermaid and the sketch, so they can't disagree.
- **Cache** `art/<name>.svg` + `art/<name>.inputhash`; redraw only when the
  hash changes materially — otherwise every cadence run burns a call and churns
  the image.
- **Exposure inherits** (§15): a box that would carry a `private-ref` label →
  generalise the *prompt* in `public` mode. Don't ask it to draw what you
  wouldn't write.
- **Model:** `freeform_canvas` defaults to `gemini-3.7-flash`; the test used
  `3.8-flash` and it laid out cleanly. That's the draw service's config to set,
  not this agent's concern.

**Where it lands:**

- **`ARCHITECTURE.md`, not `README.md`.** A marketing README's visual should be a
  product shot (the rendered UI the tool produces), not an internal diagram —
  those read as "enterprise vendor" on a landing page. `ARCHITECTURE.md` is the
  reader who wants it: someone about to change code.
- Embed as `![](assets/onboarding/architecture-sketch.svg)` at the top of §5
  "The map", with the **Mermaid module-graph directly below it**: sketch for
  orientation, Mermaid for the precise reference.
- The sketch's labels pass the same `public` / `internal` exposure filter (§15)
  as the prose — an `internal` sketch may label `ops/ (private tier)`; a `public`
  one may not.
- v2 interactive A2UI surface: an `agent_sketchpad` / `freeform_canvas` atom
  pre-loaded with the SVG.

Split rule: **Mermaid where the picture *is* the facts; the draw agent where the
picture is there to make the page inviting.**
