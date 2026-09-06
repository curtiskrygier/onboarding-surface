# author — the single governed LLM call (spec §10)

Step 3. `facts.json` + the repo's agent docs / README / a code digest → an
`authored.json` map `{section: body_md}` for the authored + hybrid sections.
`render` slots these into the marker blocks.

```
export MAISON_GEMINI_API_KEY=...            # Vertex Express key
python3 -m author facts.json --out authored.json
python3 -m author facts.json --exposure public --model gemini-3.8-flash
```

Then: `python3 -m render facts.json --authored authored.json --out-dir out/`

## What it does

One structured call. The prompt hard-enforces:
- write only from what's provided; null fact → the section's gap-flag, no guess
- no generic engineering advice; every sentence about *this* repo
- reference code by symbol, never `file.py:214`
- **landmines only from the invariant rules + history flags + agent-doc prose**;
  nothing real → `None extracted.`
- British English, plain, short; one Diátaxis mode per section

On the way out it warns on `file:line` refs and unsourced landmine bullets.
`--exposure public` adds the §15 generalisation rule for landmines.

## Verified on a2ui-catalogue (`../results/render/a2ui-catalogue-gen/`)

- **landmines** — 9 real ones pulled from CLAUDE.md/AGENTS.md, all sourced:
  `.gs` renderer as ground truth, the `mcp:<verb>` silent-failure hand-sync,
  `tools/list` parity deadlock, "deployed ≠ reachable", the `a2ui-private`
  symlink incompleteness. No fabrication.
- **first-contribution** — found the real recent `photo_grid`/`photo_stepper`
  fix and scoped it with a definition of done.
- **what-it-is** — flat (no GitHub `description`/`topics` offline). The
  `--github` adapter is what sharpens it.
