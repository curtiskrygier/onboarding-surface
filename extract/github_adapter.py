"""github_adapter.py — the opt-in online layer (extract --github).

Fills the GitHub-only fact slots: description / topics / archived,
CI status, branch-protection rules, starter issues, and review-comment
mining (a spec §6 landmine source). Uses the `gh` CLI (already authed).
Every call is best-effort; a failure records a note, never crashes.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

_REVIEW_PHRASES = re.compile(
    r"\b(we don'?t|do not|don'?t import|never call|never import|breaks the|"
    r"anti-?pattern|has to stay|must not|used to|regressed|footgun)\b", re.I)


def _gh(*args: str) -> str | None:
    try:
        r = subprocess.run(["gh", "api", *args], capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _slug(repo: Path) -> str | None:
    url = subprocess.run(
        ["git", "-C", str(repo), "config", "--get", "remote.origin.url"],
        capture_output=True, text=True).stdout.strip()
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$", url)
    return m.group(1) if m else None


def enrich(repo: Path, facts: dict) -> None:
    slug = _slug(repo)
    if not slug:
        facts["_github_error"] = "no github.com remote"
        return
    notes = []

    meta = _gh(f"repos/{slug}",
               "--jq", "{description,archived,topics:.topics,default_branch}")
    if meta:
        d = json.loads(meta)
        facts["repo"]["description"] = d.get("description")
        facts["repo"]["archived"] = d.get("archived")
        facts["repo"]["topics"] = d.get("topics") or None
    else:
        notes.append("repo metadata")

    br = facts["repo"].get("default_branch") or "main"
    prot = _gh(f"repos/{slug}/branches/{br}/protection", "--jq",
               "{checks:.required_status_checks.contexts,reviews:.required_pull_request_reviews.required_approving_review_count}")
    if prot:
        p = json.loads(prot)
        facts["contrib"]["required_checks"] = p.get("checks") or []
        facts["contrib"]["branch_rules"] = (
            f"{p['reviews']} approving review(s) required" if p.get("reviews") else "branch protection on, no review gate")
    else:
        facts["contrib"]["branch_rules"] = "no branch protection on the default branch"

    runs = _gh(f"repos/{slug}/actions/runs?branch={br}&per_page=1", "--jq",
               ".workflow_runs[0].conclusion")
    if runs:
        facts["activity"]["ci_status"] = runs.strip().strip('"') or None

    starters = []
    for label in ("good first issue", "help wanted"):
        out = _gh(f'repos/{slug}/issues?state=open&labels={label.replace(" ", "%20")}&per_page=5',
                  "--jq", '[.[] | select(.assignee == null) | {number, title, url:.html_url, comments}]')
        if out:
            starters += json.loads(out)
    if starters or _gh(f"repos/{slug}/issues?per_page=1"):   # distinguish "none" from "call failed"
        seen = set()
        facts["issues"]["starter_candidates"] = [
            s for s in starters if not (s["number"] in seen or seen.add(s["number"]))][:5]

    hits = []
    cmts = _gh(f"repos/{slug}/pulls/comments?per_page=100&sort=created&direction=desc",
               "--jq", "[.[] | {body, pr:.pull_request_url, path}]")
    if cmts:
        for c in json.loads(cmts):
            body = (c.get("body") or "").strip()
            if 8 < len(body) < 400 and _REVIEW_PHRASES.search(body):
                hits.append({
                    "snippet": re.sub(r"\s+", " ", body)[:220],
                    "pr": (c.get("pr") or "").rsplit("/", 1)[-1],
                    "path": c.get("path"),
                })
        facts["history"]["review_comment_hits"] = hits[:12]
    else:
        notes.append("review comments")

    facts["_github"] = True
    if notes:
        facts["_github_partial"] = "could not fetch: " + ", ".join(notes)
