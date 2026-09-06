# draw — the architecture sketch (spec §16b)

`facts.json` → a structured box/edge/zone spec (built here, from facts only) →
one `freeform_canvas`-shaped LLM call → a sanitised, cached SVG.

```
python3 -m draw facts.json                       # writes into the repo itself:
                                                  #   <repo>/assets/onboarding/architecture-sketch.svg
python3 -m draw facts.json --exposure public --out some/other/path.svg
python3 -m draw facts.json --detail detailed --force   # ignore the input-hash cache
```

## Not in the default pipeline

An **authored artifact** — one non-deterministic LLM call, same governance class
as `author`. `extract`/`render` never call it. Cadence only:
`onboard.py --art`, or run `draw` directly. Never per-push, never gated.

## Honesty

`build_diagram_spec()` builds the box list, edge list and zone grouping from
`facts.json` alone — real module names, real declared services, real CI +
generated-output presence, real `clone_gaps`/`sibling_repos`. The model gets
that structure and does layout only; it is told explicitly to invent no
additional boxes or relationships. `extract` doesn't do import/dependency
analysis (§16a is deferred for exactly that reason), so the edges here are only
the ones facts actually prove: containment (repo → its modules), an entrypoint
starting the repo, CI producing a declared generated-output dir, a contributor
needing a declared sibling repo or private path.

## Exposure (§15) inherits

`--exposure public` generalises any box label that would be a `private-ref`
(reusing `render.render`'s own `_private_tokens`/`_hits_private`) **before** it
reaches the prompt — the same "don't ask it to draw what you wouldn't write"
rule as the prose sections.

## Post-processing

Raw draw-agent output is never trusted as-is: `sanitise_svg()` strips
`<script>`/`<foreignObject>`/`<iframe>`/`<object>`/`<embed>`/`<image>`,
event-handler attributes, non-local `href`/`xlink:href`, `<style>` tags, and a
baked full-canvas background rect if the model drew one anyway. Never
rewrites content — flag-and-strip only, same discipline as `render`'s leak
scan.

## Cache

`<out>.svg` + `<out>.inputhash` sit side by side. A re-run with an unchanged
structured input (same facts, same exposure, same detail level) is a no-op —
`unchanged (hash …) — kept …` — so a cadence job doesn't burn a call and churn
the image on every run. `--force` bypasses it.

## Verified 2026-09-06

`a2ui-catalogue.github.json`, `gemini-3.8-flash`, both exposures: one call each,
~4–5 KB SVG, viewBox `0 0 1100 700`, 10 boxes (the overview cap), all labels
verbatim from the spec. `internal` names `ops.py`; `public` generalises it to
"a private/internal path" — nothing else differs. Sanitiser found nothing to
strip in either run (the prompt's own constraints held). Cache hit confirmed
on an identical re-run; `--force` bypassed it.

**Where `render` picks it up:** `render.sec_codemap` already checks for
`<repo>/assets/onboarding/architecture-sketch.svg` (or an authored `_has_sketch`
flag) and embeds it — no `render` changes needed for this module to take effect.
