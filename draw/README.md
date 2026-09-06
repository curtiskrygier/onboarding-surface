# draw — two visual jobs (spec §16b, §16c)

## `architecture` — the sketch (§16b, deterministic, no LLM)

`facts.json` → a structured box/edge/zone spec (built here, from facts only) →
[D2](https://d2lang.com) source → the `d2` CLI → a cached SVG.

```
python3 -m draw architecture facts.json           # -> <repo>/assets/onboarding/architecture-sketch.svg
python3 -m draw architecture facts.json --exposure public --detail detailed --out p.svg
python3 -m draw architecture facts.json --force   # ignore the input-hash cache
```

Needs the `d2` CLI on `PATH` ([install](https://d2lang.com/tour/install)). No
API key, no network call — deterministic given the same facts.

### Not in the default pipeline

Cadence only: `onboard.py --art`, or run directly. `extract`/`render` never
call it. Not gated on cost or latency any more (no LLM call left in this
path) — kept cadence-only by convention so a repo's diagram doesn't churn on
every commit.

### Honesty

`build_diagram_spec()` builds the box list, edge list and zone grouping from
`facts.json` alone — real module names, real declared services, real CI +
generated-output presence, real `clone_gaps`/`sibling_repos`. `build_d2_source()`
is a pure syntax translation of that spec — no content decisions of its own.
`extract` doesn't do import/dependency analysis (§16a is deferred for exactly
that reason), so the edges here are only the ones facts actually prove:
containment (repo → its modules), an entrypoint starting the repo, CI
producing a declared generated-output dir, a contributor needing a declared
sibling repo or private path.

### Representativeness

`facts.structure.modules` is ranked by real file count, which favours large
generic scaffolding (`tests/`, `scripts/`) over small-but-real product
surfaces when the box budget is tight. `_rank_modules()` reorders (never
drops) modules matching a generic-name pattern behind everything else, so
product code wins the limited slots — verified on a2ui-catalogue, whose
diagram used to read "apps-script-heavy, no web, no MCP" until this landed.

### Exposure (§15) inherits

`--exposure public` generalises any box label that would be a `private-ref`
(reusing `render.render`'s own `_private_tokens`/`_hits_private`) **before**
the D2 source is built.

### Cache

`<out>.svg` + `<out>.inputhash` sit side by side. A re-run with an unchanged
structured input is a no-op. `--force` bypasses it.

### Style

D2 theme 0 ("Neutral Default") — picked by comparing it side by side against
Cool Classics and hand-drawn sketch mode on the same diagram.

### Superseded

The original build called a `freeform_canvas` LLM one-shot to draw the SVG
freehand. Reverted 2026-09-06 — the model guessing box coordinates itself
never matched a real layout engine's output, no matter how the prompt was
tuned. `examples/a2ui-catalogue/architecture-sketch.svg` (the first hand-tuned
test) stays in the repo as the record of what that path could do.

## `mark` / `adopt-mark` — the repo mark (§16c, LLM, human-gated)

Unlike the sketch, a mark *invents a metaphor* — the one thing a deterministic
layout engine can't do. Stays LLM-driven, and stays a proposal a human must
pick; never auto-adopted.

```
python3 -m draw mark facts.json --n 3             # -> <repo>/assets/onboarding/mark-candidates/
python3 -m draw mark facts.json --force           # propose even if a mark already exists
python3 -m draw adopt-mark mark-2.svg --repo <repo>   # the ONLY step that writes into a repo
```

`propose_marks()` generates N candidates in one call — genuinely distinct
concepts, not colour/shape variations of one idea — each post-processed
(`postprocess_mark()`: strip a baked background, tighten the viewBox to the
real bounding box, drop redundant attrs) with a `currentColor` monochrome
variant alongside. Writes a `manifest.json` (concept + justification per
candidate) and stops. `has_existing_mark()` refuses to propose when the repo
already has one (`assets/logo*`/`favicon*`, a `.github/` brand asset, or a
logo/wordmark image in the README) unless `--force`.

`adopt_mark()` is the only function in this module that writes into a repo's
own `assets/` — always separate, explicit, human-invoked.

## Verified 2026-09-06

- `architecture`: `a2ui-catalogue`, both exposures — one `d2` compile each
  (~350ms), viewBox auto-sized to content, all labels traced to the spec,
  `mcp`/`renderers`/`cloud-run-renderer` correctly represented after the
  representativeness fix. `internal` names `ops.py`; `public` says "a
  private/internal path". Also clean on `maison` and `onboarding-surface`
  itself (small box counts).
- `mark`: `maison` (no existing mark) — 3 distinct house-themed concepts, all
  post-processed correctly; `has_existing_mark()` correctly refused on
  a2ui-catalogue and onboarding-surface (both already have one); `adopt-mark`
  verified writing all three files into a target repo.
