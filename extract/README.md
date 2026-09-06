# extract — build `facts.json` from a repo

Step 1 of the build order. Offline by default: `git` + file reads, no network,
no LLM. Everything not derivable offline is `null` → downstream emits an explicit
UNKNOWN, never an LLM prompt (spec §9).

```
python3 -m extract <repo-path>                 # facts.json to stdout
python3 -m extract <repo-path> --out f.json
python3 -m extract <repo-path> --github        # + starter issues / review mining (opt-in adapter, TODO)
```

## What it does well (verified on 3 repos — snapshots in `../results/facts/`)

| repo | `repo_kind` | notable |
|---|---|---|
| `a2ui-catalogue` | `toolkit` | 9 real `clone_gaps` (incl. `a2uithoughts.md` gitignored, `ops.py` absent), `sibling_repos: [a2ui-private]`, `public/` filtered out of language + churn |
| `maison` | `service` | FastAPI signal, `sibling_repos: [a2ui-catalogue]` |
| `onboarding-surface` | `docs` | (flips to toolkit/library once `render`/`serve` land) |

## Known rough edges (v1)

- `clone_gaps` still lets through the occasional non-path (`tools/list` — an MCP
  method) — a small denylist would clean it.
- `repo_kind` for a repo that *ships* a service as one component vs *is* a
  service leans on `ops/ops.py + project.yaml` as the toolkit tie-breaker.
- `description` / `topics` / `ci_status` / `branch_rules` / `starter_candidates`
  are GitHub-only → `null` offline, by design.
- `commit_convention` detects conventional-commits + config files; the
  `ops.py commit` / `Co-Authored-By` / `#NN` house style shows as `null`.
