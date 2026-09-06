"""facts.py — build facts.json from a local repo path.

Offline by default: git (subprocess) + file reads only, no network, no LLM.
Anything not derivable offline is `None` — downstream turns that into an
explicit UNKNOWN, never an LLM prompt (spec §9). The GitHub adapter
(starter issues, review-comment mining) is opt-in via `github=True`.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None
try:
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = None


# ── git helpers ───────────────────────────────────────────────────────────────
def _git(repo: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=30, check=False,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _tracked_files(repo: Path) -> list[str]:
    """What a fresh clone actually contains."""
    out = _git(repo, "ls-files")
    return [ln for ln in out.splitlines() if ln]


def _read(repo: Path, rel: str, limit: int = 200_000) -> str | None:
    p = repo / rel
    try:
        return p.read_text(errors="replace")[:limit] if p.is_file() else None
    except OSError:
        return None


def _exists(repo: Path, rel: str) -> bool:
    return (repo / rel).exists()


# ── repo identity ────────────────────────────────────────────────────────────
_SPDX = [
    ("MIT License", "MIT"), ("Apache License", "Apache-2.0"),
    ("GNU GENERAL PUBLIC LICENSE", "GPL"), ("Mozilla Public License", "MPL-2.0"),
    ("BSD 3-Clause", "BSD-3-Clause"), ("The Unlicense", "Unlicense"),
]


def repo_facts(repo: Path) -> dict:
    remote = _git(repo, "config", "--get", "remote.origin.url")
    name = None
    if remote:
        name = re.sub(r"\.git$", "", remote.rstrip("/").split("/")[-1]) or None
    name = name or repo.name

    lic = None
    for fn in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"):
        txt = _read(repo, fn, 4000)
        if txt:
            lic = next((k for m, k in _SPDX if m.lower() in txt.lower()), "custom")
            break

    return {
        "name": name,
        "remote": remote or None,
        "default_branch": _git(repo, "rev-parse", "--abbrev-ref", "HEAD") or None,
        "description": None,     # GitHub-only
        "topics": None,          # GitHub-only
        "license": lic,
        "archived": None,        # GitHub-only
    }


# ── activity ─────────────────────────────────────────────────────────────────
def activity_facts(repo: Path) -> dict:
    last = _git(repo, "log", "-1", "--format=%cI") or None
    n90 = _git(repo, "rev-list", "--count", "--since=90 days ago", "HEAD")
    all_tags = [t for t in _git(repo, "tag", "--sort=-creatordate").splitlines() if t]
    tags = all_tags[:20]
    semver = [t for t in all_tags if re.match(r"v?\d+\.\d+", t)]
    cadence = None
    cad_tags = semver or tags
    if len(cad_tags) >= 2:
        dates = []
        for t in cad_tags[:6]:
            d = _git(repo, "log", "-1", "--format=%cI", t)
            if d:
                dates.append(datetime.fromisoformat(d))
        if len(dates) >= 2:
            gaps = [(dates[i] - dates[i + 1]).days for i in range(len(dates) - 1)]
            cadence = round(sum(abs(g) for g in gaps) / len(gaps), 1)
    return {
        "last_commit_at": last,
        "commits_90d": int(n90) if n90.isdigit() else None,
        "tags": tags,
        "latest_tag": (semver[0] if semver else (tags[0] if tags else None)),
        "latest_release_is_semver": bool(semver),
        "tag_cadence_days": cadence,
        "ci_present": _exists(repo, ".github/workflows"),
        "ci_workflows": sorted(
            p.name for p in (repo / ".github/workflows").glob("*.y*ml")
        ) if _exists(repo, ".github/workflows") else [],
        "ci_status": None,       # GitHub-only
    }


# ── structure ────────────────────────────────────────────────────────────────
_LANG = {
    ".py": "Python", ".js": "JavaScript", ".mjs": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".jsx": "JavaScript", ".go": "Go", ".rs": "Rust",
    ".rb": "Ruby", ".java": "Java", ".kt": "Kotlin", ".c": "C", ".cpp": "C++",
    ".sh": "Shell", ".gs": "Apps Script", ".html": "HTML", ".css": "CSS",
    ".md": "Markdown", ".yml": "YAML", ".yaml": "YAML", ".json": "JSON",
}
_ENTRY_HINTS = ("main.py", "__main__.py", "app.py", "server.py", "index.js",
                "index.ts", "main.go", "main.rs", "cli.py", "wsgi.py", "asgi.py")


_GENERATED_DIR = re.compile(r"^(public|public-full|dist|build|generated|vendor|node_modules)/")


# A dir with a file in one of these counts as a real code "module" downstream
# (render's codemap table, draw's diagram boxes). Was missing .mjs/.tsx/.jsx/
# .cjs/.kt/.c/.cpp -- a real dir whose code happened to be e.g. .mjs (mcp/,
# a2ui-catalogue's real MCP surface) was silently invisible to `modules`
# entirely, not just deprioritised. Deliberately excludes markup/style/data
# extensions (.html/.css/.json/.yaml/.md) even though _LANG recognises them as
# languages -- those are generated-site/config territory, not what this means.
_CODE_EXT = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".go", ".rs",
            ".rb", ".java", ".kt", ".c", ".cpp", ".gs"}


def structure_facts(repo: Path) -> dict:
    files = _tracked_files(repo)
    dir_counts: Counter = Counter()      # ALL files, incl. generated -- for top_dirs
    real_dir_counts: Counter = Counter()  # non-generated only -- for modules ranking
    code_dirs: set[str] = set()
    lang: Counter = Counter()          # over hand-written files only
    entrypoints: list[str] = []
    generated = 0
    for f in files:
        top = f.split("/", 1)[0] if "/" in f else "(root)"
        dir_counts[top] += 1
        if _GENERATED_DIR.match(f):
            generated += 1
            continue
        real_dir_counts[top] += 1
        ext = os.path.splitext(f)[1].lower()
        if ext in _LANG:
            lang[_LANG[ext]] += 1
        if ext in _CODE_EXT:
            code_dirs.add(top)
        base = os.path.basename(f)
        if base in _ENTRY_HINTS or re.match(r"(cmd|bin)/[^/]+/main\.\w+$", f):
            entrypoints.append(f)

    # real_dir_counts.most_common() is already ranked by real (non-generated)
    # file count -- keep that order, don't alphabetise it away. Everything
    # downstream that truncates this list (render's codemap table, draw's box
    # budget) should drop the SMALLEST modules first, not whichever sorts last
    # by name -- and a directory that is ENTIRELY generated (public/, even
    # though one vendored file inside it happens to have a code extension)
    # must never qualify at all, which is why this checks real_dir_counts/
    # code_dirs rather than re-scanning the full, generated-inclusive `files`.
    modules = [d for d, _ in real_dir_counts.most_common()
              if d != "(root)" and d in code_dirs]
    # primary = most common non-Markdown code language; Markdown only if nothing else
    code_langs = [(l, c) for l, c in lang.most_common() if l != "Markdown"]
    return {
        "file_count": len(files),
        "generated_file_count": generated,
        "top_dirs": dict(dir_counts.most_common(30)),
        "languages": dict(lang.most_common()),
        "primary_language": (code_langs[0][0] if code_langs
                             else (lang.most_common(1)[0][0] if lang else None)),
        "entrypoints": sorted(set(entrypoints)),
        "modules": modules[:25],
    }


# ── run ──────────────────────────────────────────────────────────────────────
def _make_targets(repo: Path) -> list[str]:
    out = []
    for fn in ("Makefile", "Taskfile.yml", "Taskfile.yaml", "justfile", "Justfile"):
        txt = _read(repo, fn)
        if not txt:
            continue
        if fn.startswith("Makefile"):
            out += re.findall(r"^([a-zA-Z][\w-]*):", txt, re.M)
        elif fn.startswith("Taskfile"):
            out += re.findall(r"^\s{2}([a-zA-Z][\w:-]*):", txt, re.M)
        else:
            out += re.findall(r"^([a-zA-Z][\w-]*):", txt, re.M)
    return sorted(set(out))


def run_facts(repo: Path) -> dict:
    install = run = test = lint = None
    pkg = _read(repo, "package.json")
    scripts = {}
    if pkg:
        try:
            scripts = json.loads(pkg).get("scripts", {}) or {}
        except json.JSONDecodeError:
            pass
        install = "npm install"
        run = "npm run " + ("dev" if "dev" in scripts else "start") if ("dev" in scripts or "start" in scripts) else None
        test = "npm test" if "test" in scripts else None
        lint = "npm run lint" if "lint" in scripts else None
    if _exists(repo, "requirements.txt") or _exists(repo, "pyproject.toml"):
        install = install or "pip install -r requirements.txt" if _exists(repo, "requirements.txt") else install or "pip install -e ."
        test = test or ("python3 -m pytest" if _exists(repo, "tests") or _exists(repo, "test") else None)

    services = []
    for fn in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        txt = _read(repo, fn)
        if txt and yaml:
            try:
                services = list((yaml.safe_load(txt) or {}).get("services", {}).keys())
            except yaml.YAMLError:
                pass
            break

    env_vars = []
    for fn in (".env.example", ".env.sample", ".env.template", ".env.dist"):
        txt = _read(repo, fn)
        if txt:
            env_vars = re.findall(r"^\s*([A-Z][A-Z0-9_]+)\s*=", txt, re.M)
            break

    tool_versions = {}
    for fn, key in ((".nvmrc", "node"), (".tool-versions", "*"),
                    ("rust-toolchain.toml", "rust"), (".python-version", "python")):
        txt = _read(repo, fn, 2000)
        if txt:
            tool_versions[key] = txt.strip().splitlines()[0] if key != "*" else txt.strip()

    setup_targets = [t for t in _make_targets(repo)
                     if re.search(r"setup|bootstrap|init|install|dev", t, re.I)]
    migration_dirs = [d for d in ("migrations", "db/migrate", "alembic", "prisma/migrations")
                      if _exists(repo, d)]

    return {
        "install_cmd": install,
        "run_cmd": run,
        "test_cmd": test,
        "lint_cmd": lint,
        "make_targets": _make_targets(repo)[:40],
        "setup_targets": setup_targets,
        "services": services,
        "env_var_names": sorted(set(env_vars)),
        "tool_versions": tool_versions,
        "migration_dirs": migration_dirs,
        "needs_node_binary": bool(_read(repo, "requirements.txt") and "node" in (_read(repo, "requirements.txt") or "").lower()),
    }


# ── invariants ───────────────────────────────────────────────────────────────
def invariant_facts(repo: Path) -> dict:
    rules: list[str] = []
    configs: list[str] = []
    for fn in (".dependency-cruiser.js", ".dependency-cruiser.json", ".dependency-cruiser.cjs"):
        if _exists(repo, fn):
            configs.append(fn)
            rules += [f"dependency-cruiser: {m}" for m in
                      re.findall(r'name:\s*[\'"]([^\'"]+)[\'"]', _read(repo, fn) or "")][:15]
    for fn in (".importlinter", "importlinter.ini", "setup.cfg", "pyproject.toml"):
        txt = _read(repo, fn)
        if txt and "importlinter" in txt.lower():
            configs.append(fn)
            rules += [f"import-linter: {m}" for m in re.findall(r"^name\s*=\s*(.+)$", txt, re.M)][:15]
    esl = None
    for fn in (".eslintrc.js", ".eslintrc.json", ".eslintrc.cjs", ".eslintrc.yml", "eslint.config.js", "eslint.config.mjs"):
        if _exists(repo, fn):
            esl = fn
            break
    if esl:
        txt = _read(repo, esl) or ""
        if "boundaries" in txt or "import/no-restricted" in txt or "no-restricted-imports" in txt:
            rules.append(f"eslint boundary rules in {esl}")

    files = _tracked_files(repo)
    go_internal = sorted({f.split("internal/")[0] + "internal/" for f in files if "/internal/" in f or f.startswith("internal/")})
    return {
        "config_files": sorted(set(configs)) + ([esl] if esl else []),
        "boundary_rules": rules,
        "go_internal_pkgs": go_internal[:10],
    }


# ── history ──────────────────────────────────────────────────────────────────
_GENERATED_HINT = re.compile(r"(^|/)(public|dist|build|generated|\.generated|vendor|node_modules)(/|$)")


def history_facts(repo: Path, n: int = 250) -> dict:
    # tightened: `Revert "` (git's own revert subject) or an explicit regression
    # phrase in the SUBJECT — the old broad multi-grep over the whole body
    # caught unrelated commits that merely mention "stale" in passing.
    reverts = []
    for ln in _git(repo, "log", "--pretty=format:%s", "-400").splitlines():
        if re.match(r'Revert "', ln) or re.search(r"\b(regression|regressed|broke\b|fixes a real)\b", ln, re.I):
            reverts.append(ln.strip())

    churn: Counter = Counter()
    raw = _git(repo, "log", f"-{n}", "--name-only", "--pretty=format:%H")
    cur_files: list[str] = []
    for ln in raw.splitlines():
        if not ln.strip():
            continue
        if re.fullmatch(r"[0-9a-f]{7,40}", ln):
            cur_files = []
            continue
        if _GENERATED_HINT.search(ln):
            continue
        top = ln.split("/", 1)[0] if "/" in ln else "(root)"
        churn[top] += 1
    return {
        "revert_commits": reverts[:12],
        "churn_by_dir": dict(churn.most_common(12)),
        "review_comment_hits": None,   # GitHub-only
    }


# ── contrib ──────────────────────────────────────────────────────────────────
def contrib_facts(repo: Path) -> dict:
    recent = _git(repo, "log", "-40", "--format=%B")
    dco = "Signed-off-by:" in recent
    cla = any(_exists(repo, p) for p in (".github/workflows/cla.yml",)) or \
        bool(re.search(r"cla", " ".join(
            p.name for p in (repo / ".github/workflows").glob("*")) if _exists(repo, ".github/workflows") else "", re.I))
    commit_conv = None
    for fn in ("commitlint.config.js", "commitlint.config.cjs", ".commitlintrc", ".czrc"):
        if _exists(repo, fn):
            commit_conv = fn
            break
    if not commit_conv and re.search(r"^(feat|fix|chore|docs|refactor)(\(.+\))?:", recent, re.M):
        commit_conv = "conventional-commits (observed in history, no config)"
    elif not commit_conv:
        hints = []
        if recent.count("Co-Authored-By:") >= 5:
            hints.append("commits carry a Co-Authored-By trailer")
        if len(re.findall(r"\(#\d+\)\s*$", recent, re.M)) >= 5:
            hints.append("subjects end with a (#NN) PR reference")
        if hints:
            commit_conv = "house style: " + "; ".join(hints)

    pr_template = None
    for fn in (".github/PULL_REQUEST_TEMPLATE.md", ".github/pull_request_template.md",
               "docs/PULL_REQUEST_TEMPLATE.md"):
        txt = _read(repo, fn)
        if txt:
            pr_template = re.findall(r"^#+\s*(.+)$", txt, re.M)[:8]
            break

    return {
        "has_contributing_md": _exists(repo, "CONTRIBUTING.md") or _exists(repo, ".github/CONTRIBUTING.md"),
        "cla": bool(cla),
        "dco": dco,
        "commit_convention": commit_conv,
        "pr_template_fields": pr_template,
        "branch_rules": None,          # GitHub-only (branch protection)
        "required_checks": None,       # GitHub-only
    }


# ── docs ─────────────────────────────────────────────────────────────────────
_AGENT_DOCS = ("CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursorrules", ".github/copilot-instructions.md")


def docs_facts(repo: Path) -> dict:
    readme = _read(repo, "README.md") or _read(repo, "readme.md") or ""
    sections = re.findall(r"^#{1,3}\s+(.+?)\s*$", readme, re.M)
    doc_dirs = [d for d in ("docs", "doc", "documentation") if _exists(repo, d)]
    return {
        "readme_sections": sections[:20],
        "readme_len": len(readme),
        "has_architecture_md": _exists(repo, "ARCHITECTURE.md"),
        "has_contributing_md": _exists(repo, "CONTRIBUTING.md"),
        "agent_docs": [d for d in _AGENT_DOCS if _exists(repo, d)],
        "doc_dirs": doc_dirs,
        "spec_dir": _exists(repo, "spec"),
    }


# ── v0.2 facts ───────────────────────────────────────────────────────────────
_PATHY_EXT = re.compile(
    r"\.(py|js|mjs|cjs|ts|tsx|jsx|go|rs|rb|java|gs|sh|md|ya?ml|json|toml|ini|cfg|html|css|txt)$")


# backticked tokens that look pathy but are API surface / config keys, not files
_NOT_A_PATH = {
    "tools/list", "tools/call", "resources/list", "prompts/list", "n/a",
    "and/or", "http/https", "input/output", "read/write", "client/server",
    "src/main", "os/exec",
}


def _looks_like_repo_path(cand: str) -> bool:
    """A backticked token that plausibly names a file IN THIS repo — not a URL
    fragment, an absolute path, an API method, or a code identifier."""
    if cand.lower() in _NOT_A_PATH:
        return False
    if cand.startswith(("http", "/", "~", ".")) or " " in cand:
        return False
    if re.match(r"[\w-]+\.(ai|com|org|io|dev|net)(/|$)", cand):     # domain
        return False
    if cand.startswith(("home/", "Users/", "var/", "tmp/", "etc/")):  # abs fragment
        return False
    if _PATHY_EXT.search(cand):
        return True
    # a slash path where each segment is a real dir/file name (no prose "a/b")
    if "/" in cand and all(re.match(r"[\w.-]+$", s) for s in cand.split("/")) \
       and any(len(s) > 2 for s in cand.split("/")):
        return True
    return False


def clone_gap_facts(repo: Path) -> dict:
    """Paths named in docs but gitignored or absent from a clone (spec §15)."""
    gaps: list[dict] = []
    seen = set()
    for src in ("README.md", "CLAUDE.md", "AGENTS.md", "CONTRIBUTING.md", "GEMINI.md"):
        txt = _read(repo, src)
        if not txt:
            continue
        for cand in re.findall(r"`([^`\s]+)`", txt):
            cand = cand.strip("`/.,")
            if cand in seen or not _looks_like_repo_path(cand):
                continue
            seen.add(cand)
            if (repo / cand).exists():
                ignored = subprocess.run(
                    ["git", "-C", str(repo), "check-ignore", "-q", cand],
                    capture_output=True, check=False).returncode == 0
                if ignored:
                    gaps.append({"path": cand, "in": src, "why": "gitignored"})
            else:
                # only report a real absence if a sibling by basename also isn't tracked
                base = os.path.basename(cand)
                tracked = _tracked_files(repo)
                if not any(f.endswith("/" + base) or f == base for f in tracked):
                    gaps.append({"path": cand, "in": src, "why": "absent"})
    return {"clone_gaps": gaps[:20]}


def sibling_repo_facts(repo: Path) -> dict:
    hits = set()
    for src in ("README.md", "CLAUDE.md", "AGENTS.md"):
        txt = _read(repo, src) or ""
        for m in re.findall(r"\.\./([a-z][\w-]+)(?:/|\b)", txt):
            hits.add(m)
    # also scan a couple of config files
    for fn in ("project.yaml", "package.json", "Makefile"):
        txt = _read(repo, fn) or ""
        for m in re.findall(r"\.\./([a-z][\w-]+)/", txt):
            hits.add(m)
    return {"sibling_repos": sorted(hits)}


_WEB_DEP = re.compile(r"\b(fastapi|flask|django|starlette|express|koa|gin|axum|actix|rails|next)\b", re.I)


def repo_kind(repo: Path, structure: dict, run: dict, docs: dict) -> str:
    files = set(_tracked_files(repo))
    reqs = (_read(repo, "requirements.txt") or "") + (_read(repo, "pyproject.toml") or "") + \
           (_read(repo, "package.json") or "") + (_read(repo, "go.mod") or "")
    dockerfile = _read(repo, "Dockerfile") or ""

    # monorepo first — unambiguous
    if any(f.startswith(("packages/", "apps/")) for f in files) or _exists(repo, "pnpm-workspace.yaml"):
        return "monorepo"

    # docs — overwhelmingly prose
    total_code = sum(c for l, c in structure["languages"].items() if l != "Markdown")
    md = structure["languages"].get("Markdown", 0)
    if total_code < 5 and md > 0:
        return "docs"

    # toolkit — the declared-process-runner pattern (project.yaml + ops/ops.py).
    # Strong signal; beats a Dockerfile that only builds one sub-component.
    if _exists(repo, "ops/ops.py") and _exists(repo, "project.yaml"):
        return "toolkit"

    # service — needs a real server signal, not just a Dockerfile
    server_entry = any(re.search(r"(server|asgi|wsgi|main)\.\w+$", e) for e in structure["entrypoints"])
    if run["services"] or _exists(repo, "Procfile") or "EXPOSE" in dockerfile \
       or _WEB_DEP.search(reqs) or (server_entry and _WEB_DEP.search(reqs + dockerfile)):
        return "service"

    # toolkit — a declared-process runner / generators, no importable package surface
    if (_exists(repo, "ops/ops.py") or _exists(repo, "project.yaml")) and not _exists(repo, "pyproject.toml"):
        return "toolkit"

    # library — has a package/entry surface
    if _exists(repo, "pyproject.toml") or _exists(repo, "setup.py") or \
       (_read(repo, "package.json") and '"main"' in (_read(repo, "package.json") or "")):
        return "library"
    return "toolkit"


# ── assemble ─────────────────────────────────────────────────────────────────
def build(repo_path: str | Path, *, github: bool = False) -> dict:
    repo = Path(repo_path).resolve()
    if not (repo / ".git").exists():
        raise SystemExit(f"not a git repo: {repo}")

    structure = structure_facts(repo)
    run = run_facts(repo)
    docs = docs_facts(repo)
    facts = {
        "_generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "_repo_path": str(repo),
        "_github": github,
        "repo": repo_facts(repo),
        "activity": activity_facts(repo),
        "structure": structure,
        "run": run,
        "invariants": invariant_facts(repo),
        "history": history_facts(repo),
        "contrib": contrib_facts(repo),
        "docs": docs,
        "clone_gaps": clone_gap_facts(repo)["clone_gaps"],
        "sibling_repos": sibling_repo_facts(repo)["sibling_repos"],
        "repo_kind": repo_kind(repo, structure, run, docs),
        "issues": {"starter_candidates": None},   # GitHub-only
    }
    if github:
        try:
            from extract.github_adapter import enrich  # noqa: PLC0415
            enrich(repo, facts)
        except Exception as e:  # noqa: BLE001
            facts["_github_error"] = str(e)
    return facts


if __name__ == "__main__":
    import sys
    print(json.dumps(build(sys.argv[1]), indent=2))
