# render — facts.json (+ authored) → the three Markdown files

Step 2. Deterministic section bodies (`maturity`, `pr-gates`, `pointers`, and
the machine parts of `run-it` / `codemap` / `verify`) are produced here — no LLM.
Authored prose comes from an `authored.json` map keyed by section name; step 3
`author` produces it. A missing authored body renders as
`<!-- authored: pending -->`, never a guess.

```
python3 -m render facts.json --authored authored.json --out-dir out/
python3 -m render facts.json --fresh          # emit only the blocks, ignore existing files
python3 -m render facts.json --exposure public
```

## Output

Marker blocks (`<!-- onboarding-surface:begin/end SECTION -->`) spliced into:

| file | sections |
|---|---|
| `README.md` | what-it-is · maturity · orientation · run-it · pointers |
| `ARCHITECTURE.md` | codemap · landmines |
| `CONTRIBUTING.md` | first-contribution · pr-gates · verify |

Content outside the markers is preserved (unless `--fresh`).

## Verified (fresh renders in `../results/render/`)

- `a2ui-catalogue` (toolkit) — run-it opens "no server to start"; the `ops.py`
  clone-gap surfaces as an UNKNOWN in run-it; `../a2ui-private` noted; `pointers`
  lists the gitignored `a2uithoughts.md` / `improve.yaml`.
- `maison` (service) — no "toolkit" framing; missing env/services gap-flagged
  honestly; `../a2ui-catalogue` sibling noted.

## v1 limits

- The Mermaid graph is nodes only — no edges (needs import analysis; a module
  list is honest for now).
- Everything driven by `facts.json`; a `null` fact → an explicit UNKNOWN.
