# review — the HITL review page

Read-only. Shows what `render` produced for one repo, what a maintainer must
check, and the diff against the repo's current docs. **No approve/reject** — that
gate is `--pr` (not built).

```
python3 -m review --facts facts.json --docs <rendered-docs-dir> --repo <repo-path> --out review.html
```

Static HTML, no JS libraries. Open it locally.

## What it shows

- **Summary bar** — sections total, authored+hybrid ("read these"), UNKNOWNs
  ("check these"), clone gaps.
- **Section table** — each section's `kind` (deterministic / authored / hybrid)
  and `confidence`. Deterministic rows are just facts; spend your attention on
  the authored + hybrid ones.
- **The gaps to check** — every `> **UNKNOWN**` the pipeline emitted, with its
  section. This is the real maintainer to-do list.
- **Architecture sketch** — inline, if one was drawn (§16b).
- **The docs** — each proposed file rendered, plus a collapsible unified diff
  against what's in the repo now.

## Verified

`a2ui-catalogue` (`--github --exposure public`): 10-row section table, 2 real
gaps (`ops.py` absent, branch-protection GitHub-only), 3 diffs. `~/Downloads/`.
