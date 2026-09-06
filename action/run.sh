#!/usr/bin/env bash
# run.sh — the composite action's actual orchestration. Formatter, not gate
# (spec §11): every early-return below is `exit 0`, never a non-zero exit —
# this script's job is to leave good docs behind when it can, and say why
# clearly when it can't, but never turn doc generation into a required check.
set -uo pipefail  # deliberately NOT `set -e` — a step failing mid-pipeline
                  # degrades to "skip the rest, report it", not a build failure.

FACTS=/tmp/onboarding-surface-facts.json
AUTHORED=/tmp/onboarding-surface-authored.json
SKETCH_REL="assets/onboarding/architecture-sketch.svg"
TRACKED_PATHS=(README.md ARCHITECTURE.md CONTRIBUTING.md MAINTAINER-NOTES.md "$SKETCH_REL")

echo "onboarding-surface: mode=$ONBOARDING_SURFACE_MODE exposure=$ONBOARDING_SURFACE_EXPOSURE art=$ONBOARDING_SURFACE_ART"

# ── 1. extract (always, offline + optional --github adapter) ───────────────
EXTRACT_ARGS=(. --out "$FACTS")
[ "$ONBOARDING_SURFACE_GITHUB_ADAPTER" = "true" ] && EXTRACT_ARGS+=(--github)
if ! python3 -m extract "${EXTRACT_ARGS[@]}"; then
    echo "::warning::onboarding-surface: extract failed — no docs generated this run."
    echo "changed=false" >> "$GITHUB_OUTPUT"
    exit 0
fi

# ── 2. author (mode=full only, needs a real key) ────────────────────────────
AUTHOR_FLAG=()
author_ran="false"
if [ "$ONBOARDING_SURFACE_MODE" = "full" ]; then
    if [ -z "${MAISON_GEMINI_API_KEY:-}" ]; then
        echo "::warning::onboarding-surface: mode=full but gemini-api-key is empty — rendering deterministic sections only."
    elif python3 -m author "$FACTS" --out "$AUTHORED" --exposure "$ONBOARDING_SURFACE_EXPOSURE"; then
        AUTHOR_FLAG=(--authored "$AUTHORED")
        author_ran="true"
    else
        echo "::warning::onboarding-surface: author step failed — rendering deterministic sections only."
    fi
fi

# ── 3. draw (optional, before render so render's own embed check finds it) ──
draw_ran="false"
if [ "$ONBOARDING_SURFACE_ART" = "true" ]; then
    if ! command -v d2 >/dev/null 2>&1; then
        echo "installing d2..."
        curl -fsSL https://d2lang.com/install.sh | sh -s -- --quiet || \
            echo "::warning::onboarding-surface: could not install d2 — skipping the architecture sketch."
    fi
    if command -v d2 >/dev/null 2>&1; then
        if python3 -m draw architecture "$FACTS" --out "$SKETCH_REL" \
                --exposure "$ONBOARDING_SURFACE_EXPOSURE"; then
            draw_ran="true"
        else
            echo "::warning::onboarding-surface: draw failed — continuing without a sketch."
        fi
    fi
fi

# ── 4. render (in-place: splices into whatever's already here, never --fresh) ──
if ! python3 -m render "$FACTS" "${AUTHOR_FLAG[@]}" --exposure "$ONBOARDING_SURFACE_EXPOSURE" --out-dir .; then
    echo "::warning::onboarding-surface: render failed — no docs written this run."
    echo "changed=false" >> "$GITHUB_OUTPUT"
    exit 0
fi

# ── 5. did anything actually change? ────────────────────────────────────────
EXISTING_PATHS=()
for p in "${TRACKED_PATHS[@]}"; do
    [ -f "$p" ] && EXISTING_PATHS+=("$p")
done
if [ ${#EXISTING_PATHS[@]} -eq 0 ] || git diff --quiet -- "${EXISTING_PATHS[@]}"; then
    echo "onboarding-surface: no doc changes."
    echo "changed=false" >> "$GITHUB_OUTPUT"
    echo "pr-url=" >> "$GITHUB_OUTPUT"
    exit 0
fi
echo "changed=true" >> "$GITHUB_OUTPUT"

git config user.name "onboarding-surface[bot]"
git config user.email "actions@users.noreply.github.com"

# ── 6a. mode=check: commit straight into the same push ──────────────────────
if [ "$ONBOARDING_SURFACE_MODE" = "check" ]; then
    is_fork_pr="false"
    if [ "${GITHUB_EVENT_NAME:-}" = "pull_request" ] && [ -n "${GITHUB_EVENT_PATH:-}" ]; then
        head_repo=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['pull_request']['head']['repo']['full_name'])" "$GITHUB_EVENT_PATH" 2>/dev/null || echo "")
        [ -n "$head_repo" ] && [ "$head_repo" != "${GITHUB_REPOSITORY:-}" ] && is_fork_pr="true"
    fi
    if [ "$is_fork_pr" = "true" ]; then
        echo "::notice::onboarding-surface: fork PR — can't push. Diff for a maintainer to apply:"
        git diff -- "${EXISTING_PATHS[@]}"
        echo "pr-url=" >> "$GITHUB_OUTPUT"
        exit 0
    fi
    git add "${EXISTING_PATHS[@]}"
    git commit -m "docs: refresh deterministic sections (onboarding-surface)" -q
    if git push; then
        echo "onboarding-surface: pushed the refreshed sections."
    else
        echo "::warning::onboarding-surface: could not push (branch protection? fork?) — leaving the diff uncommitted."
    fi
    echo "pr-url=" >> "$GITHUB_OUTPUT"
    exit 0
fi

# ── 6b. mode=full: one PR, updated in place on re-run (never one per merge) ──
BRANCH="onboarding-surface/docs-refresh"
git checkout -B "$BRANCH" -q
git add "${EXISTING_PATHS[@]}"
# Only claim what actually ran (a fabricated "author" here when the key was
# missing or the call failed would be exactly the kind of overclaim this
# whole tool exists to prevent in the DOCS it writes -- the commit message
# describing its own run gets the same standard).
steps="render"
[ "$author_ran" = "true" ] && steps="author + $steps"
[ "$draw_ran" = "true" ] && steps="$steps + draw"
git commit -m "docs: refresh onboarding surface ($steps)" -q
if ! git push -f origin "$BRANCH" -q; then
    echo "::warning::onboarding-surface: could not push $BRANCH — no PR opened this run."
    echo "pr-url=" >> "$GITHUB_OUTPUT"
    exit 0
fi
existing_url=$(gh pr list --head "$BRANCH" --state open --json url --jq '.[0].url' 2>/dev/null || echo "")
if [ -n "$existing_url" ]; then
    echo "onboarding-surface: updated existing PR $existing_url"
    echo "pr-url=$existing_url" >> "$GITHUB_OUTPUT"
else
    url=$(gh pr create --title "docs: refresh onboarding surface" \
        --body "Automated by onboarding-surface (mode=full) — includes an LLM-authored pass. Review before merging; this never auto-merges." \
        --head "$BRANCH" 2>/dev/null || echo "")
    if [ -n "$url" ]; then
        echo "onboarding-surface: opened $url"
        echo "pr-url=$url" >> "$GITHUB_OUTPUT"
    else
        echo "::warning::onboarding-surface: pushed $BRANCH but could not open a PR (permissions?) — open one manually."
        echo "pr-url=" >> "$GITHUB_OUTPUT"
    fi
fi
exit 0
