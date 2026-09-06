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
- `--github` fills `description` / `topics` / `archived` / `ci_status` /
  `branch_rules` / `required_checks` / `starter_candidates` and mines closed-PR
  review comments for landmine phrases (a spec §6 source). Best-effort per call;
  `_github_partial` records anything that didn't fetch. Measured effect: with the
  real `description` fed in, `author`'s `what-it-is` goes from vague to naming
  the surfaces + "MCP server" + "no signup".
- `commit_convention` detects conventional-commits + config files; the
  `ops.py commit` / `Co-Authored-By` / `#NN` house style shows as `null`.
