# Pressure-test notes — a2ui-catalogue against spec v0.1

Hand-applying the spec to a real, hard repo (28 top-level dirs, private-tier
`ops/`, generated `public/`, a declarative process model, a cross-repo sibling
dependency). What it surfaced:

## What worked

- **Section 6 (landmines) is the payoff, and the sourcing rule holds.** Every
  landmine came from `CLAUDE.md`, `requirements.txt`'s header, `ops/project-ops.yaml`
  process notes, or an invariant test — *not* the file tree. Zero generic dogma.
  A repo with a rich `CLAUDE.md` / `AGENTS.md` produces a killer section for free.
- **The anti-fabrication rule earns its keep immediately.** "How do I regenerate
  the catalogue from a public clone" is genuinely UNKNOWN — `ops/` isn't there.
  A naive generator would confidently print `python3 ops/ops.py run catalog-rebuild`
  (it's in `CLAUDE.md`!) and every reader would hit `No such file`. Saying UNKNOWN
  is the correct, trust-building output.
- **`atoms/schema.yaml` as "the one mental model"** dropped out of the churn data
  (`public/` is 2699/200 commits, all generated from it) + the generator list. That
  single sentence is the highest-value line in the whole surface.
- **Diátaxis separation held** — orientation stays "why", run-it stays imperative,
  the codemap stays a lookup table.

## Spec gaps found → fold into v0.2

1. **"Private tier / not in a clone" needs to be a first-class concept.** This
   repo's documented workflow (`ops.py run …`, `a2uithoughts.md`) is *invisible to
   the actual audience*. The spec should have the extractor flag "path referenced
   in docs but absent / gitignored" and every section that leans on it should
   gap-flag. Add a `facts.clone_gaps[]` field.

2. **"Run it" assumes a runnable thing.** This repo has no server — "running" is
   the generator+test pipeline. The spec's `run` subsections (services, env,
   first-run state) mostly came back empty, which is *correct* but the section
   needs a "this repo is a library/toolkit, not a service" shape so it doesn't
   read as a pile of UNKNOWNs. Add a `repo_kind` fact: `service | library |
   toolkit | monorepo | docs`.

3. **CI adapter files matter as landmines, not just as gates.** `requirements.txt`
   ↔ `deploy.yml` hand-sync is landmine #9 and it came from a *code comment in a
   config file*, which §6's sources list doesn't mention. Add "config-file prose"
   (comments in CI yml, Makefiles, `.tool-versions`) as a §6 source.

4. **Cross-repo dependencies.** Half of `ops/project-ops.yaml`'s processes reach
   into `../a2ui-private`. The surface should state "needs sibling `a2ui-private`
   checked out for X" — the spec has no place for that. Add `facts.sibling_repos[]`.

5. **Starter-issue fallback fired.** Labels exist, zero issues carry them. The
   "smallest recent changes" fallback (§7) worked but "add or fix one atom" is a
   *judgement* — the extractor can't produce it. Accept that §7's "a well-scoped
   first change" line is authored-from-the-codemap, not derivable.

6. **The surface over-shares on a public repo.** The landmines section amplifies
   candour that was buried in `CLAUDE.md` into a front-and-centre
   `ARCHITECTURE.md`, names the private sibling repo and its files, and describes
   a silent-failure mode. Contributor-honest, adopter-alarming, competitor-useful.
   → drove spec §15's `exposure: internal|public` mode + the
   `operational|exploitable|private-ref` landmine class. See
   `landmines-exposure-demo.md` for the 11 real landmines run through `public`.

## Verdict

The spec survives a hard repo. The `README.md` / `ARCHITECTURE.md` /
`CONTRIBUTING.md` here are the `exposure: internal` rendering (full candour —
correct for a private worked example). `landmines-exposure-demo.md` shows the
`public` rendering.

Biggest v0.2 changes, all now in spec §15: `clone_gaps`, `repo_kind`,
`sibling_repos` (deterministic facts that otherwise make the surface quietly
wrong), config-file prose as a landmines source, and the `exposure` mode +
landmine class.
