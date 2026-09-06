# action — the CI adapter (spec §11)

A composite GitHub Action. Formatter, not gate: `mode=check` regenerates the
deterministic sections and commits them into the same push — never a required
status check, never a failed build. `mode=full` also runs the governed LLM
`author` step and opens one PR (never one per merge — updates the same PR on
re-run).

## Use it (now that `onboarding-surface` is public)

```yaml
# .github/workflows/docs.yml
name: onboarding-surface
on:
  push:
    branches: [main]
    paths: ['**.py', '**.js', 'Makefile', '.github/**', 'ARCHITECTURE.md']
  schedule:
    - cron: '0 6 * * 1'   # weekly mode=full

permissions:
  contents: write
  pull-requests: write

jobs:
  check:
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: curtiskrygier/onboarding-surface@v1
        with:
          mode: check

  full:
    if: github.event_name == 'schedule'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: curtiskrygier/onboarding-surface@v1
        with:
          mode: full
          gemini-api-key: ${{ secrets.MAISON_GEMINI_API_KEY }}
          art: 'true'
```

This is the in-runner path (§ below "How a2ui-catalogue's cross-account case
gets solved"): each consuming repo brings its own `MAISON_GEMINI_API_KEY`
secret and runs the pipeline directly in its own CI, no deployed service
required. `serve/` (the A2A wrapper) is a separate, optional integration for
callers who want a remote endpoint instead — see `serve/README.md`.

## Inputs

| input | default | meaning |
|---|---|---|
| `mode` | *(required)* | `check` (deterministic, same-push commit) or `full` (+ author, opens one PR) |
| `exposure` | `internal` | `internal` or `public` (spec §15) |
| `art` | `false` | also generate the architecture sketch (installs the `d2` CLI if missing) |
| `gemini-api-key` | `''` | needed for `mode=full`; `mode=check` never calls an LLM |
| `github-token` | `${{ github.token }}` | needs `contents:write` (+ `pull-requests:write` for `mode=full`) |
| `github-adapter` | `true` | pass `--github` to `extract` (starter issues, review-mined landmines) |

## Outputs

| output | meaning |
|---|---|
| `changed` | `"true"` if any doc content changed this run |
| `pr-url` | the opened/updated PR (`mode=full` only) |

## What it actually does (`run.sh`)

1. `extract` (always) — offline + `--github` by default.
2. `author` (`mode=full` only, needs `gemini-api-key`) — degrades to
   deterministic-only with a warning if the key is missing or the call fails,
   never halts the run.
3. `draw architecture` (`art: 'true'` only) — installs `d2` if it isn't
   already on the runner, before `render` so `render`'s own embed check finds
   the sketch file.
4. `render`, **always in-place** (never `--fresh`) — splices into whatever
   `README.md`/`ARCHITECTURE.md`/`CONTRIBUTING.md` already exist at the
   caller's repo root, exactly like `prettier --write`.
5. Diffs the tracked doc paths. Nothing changed → `changed=false`, exit
   cleanly.
6. `mode=check`: commits and pushes to the current ref. On a fork PR (can't
   push), posts the diff as a `::notice::` instead and exits cleanly — never
   fails the check.
7. `mode=full`: commits to a fixed branch (`onboarding-surface/docs-refresh`)
   and opens one PR, or updates the existing one from that branch if it's
   still open.

Every failure path is a `::warning::` and a clean `exit 0` — this script never
returns non-zero. That's deliberate (spec §11: "Never a required status check
on doc content"), not an oversight in the error handling.

## A real bug this surfaced (fixed in `render/render.py`)

`sec_maturity`'s commit-count text (`"quiet — 4 commits in the last 90
days"`) used an **exact** number. A formatter that diffs and commits its own
output would never converge — its own commit is itself one more commit in the
window, so the next run always finds a "change" and commits again, forever.
Verified live against a scratch repo: two consecutive runs each found a
change for no reason but the previous run's own commit. Fixed by bucketing
the count (`"a few"` / `"some"` / `"~40"` / …) instead of showing it exactly —
verified to converge to `changed=false` within two runs and stay there.

## Verified 2026-09-06

Against a real scratch git repo (not a hosted CI run, but every `git`
operation is real, nothing mocked except `GITHUB_OUTPUT`/`GITHUB_EVENT_PATH`):
`mode=check` splices correctly in place (hand-written content above the
markers survives, generated sections land inside them); running it twice more
converges to `changed=false` and stays there; a fork-PR `GITHUB_EVENT_PATH`
correctly skips the push and prints the diff instead of failing; `mode=full`
with no `gemini-api-key` degrades to a deterministic-only commit with an
honest commit message (`"docs: refresh onboarding surface (render)"`, not
falsely claiming `author` ran).

Not yet verified: a real run inside hosted GitHub Actions (this repo's own
`.github/workflows/` doesn't call the action on itself yet), the `art: true`
path's `d2` auto-install on a real runner, and `mode=full`'s PR-open/PR-update
path against a real GitHub API (only the local git branch/commit side was
exercised — `gh pr create`/`gh pr list` need a real token and repo).
