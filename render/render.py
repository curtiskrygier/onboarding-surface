"""render.py — facts.json (+ authored records) -> README / ARCHITECTURE / CONTRIBUTING.

Deterministic section bodies (maturity, pr-gates, pointers, and the machine
parts of run-it / codemap / verify) are produced HERE, no LLM. Authored/hybrid
prose comes from an `authored.json` map (step 3 `author` produces it; hand-write
it to test). Missing authored body -> an explicit `authored: pending` marker,
never a guess.

    python3 -m render facts.json --authored authored.json --out-dir ./out
    python3 -m render facts.json --exposure public
"""
from __future__ import annotations

import json
import re
from pathlib import Path

BEGIN = "<!-- onboarding-surface:begin {} -->"
END = "<!-- onboarding-surface:end {} -->"


# ── small helpers ────────────────────────────────────────────────────────────
def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def _flag(msg: str) -> str:
    return f"> **UNKNOWN** — {msg}"


def _authored(records: dict, name: str, *, fallback: str = "") -> str:
    body = (records or {}).get(name)
    if body:
        return body.strip()
    return fallback or "<!-- authored: pending — run `python3 -m author` -->"


# ── deterministic section renderers ─────────────────────────────────────────
def sec_maturity(f: dict) -> str:
    a = f["activity"]
    bits = []
    if a["commits_90d"] is not None:
        pace = ("near-daily" if a["commits_90d"] > 60 else
                "active" if a["commits_90d"] > 10 else "quiet")
        bits.append(f"{pace} — {a['commits_90d']} commits in the last 90 days")
    if a["latest_tag"]:
        tag = a["latest_tag"]
        bits.append(f"latest release `{tag}`" if a.get("latest_release_is_semver")
                    else f"latest tag `{tag}` (not a semver release)")
    if a["ci_present"]:
        bits.append(f"CI: {', '.join(a['ci_workflows'])}" if a["ci_workflows"] else "CI configured")
    if f["repo"]["archived"]:
        bits.insert(0, "**archived**")
    return ("; ".join(bits) + ".") if bits else _flag("no commit history readable")


def sec_run_it(f: dict, records: dict) -> str:
    r, kind = f["run"], f["repo_kind"]
    out = []
    if kind in ("library", "toolkit", "docs"):
        out.append(f"This repo is a **{kind}** — there is no server to start. "
                   "\"Running it\" means the build/test pipeline below.")
    out.append("")

    sysreq = []
    if r["tool_versions"]:
        sysreq += [f"`{k}` {v}" if k != "*" else v for k, v in r["tool_versions"].items()]
    if r["needs_node_binary"]:
        sysreq.append("a `node` binary on `PATH` (real subprocess in tests)")
    out.append(f"**System prerequisites:** {', '.join(sysreq)}." if sysreq
               else _flag("system packages / language versions — none declared; ask a maintainer"))

    if r["services"]:
        out.append(f"**Running services required:** {', '.join('`'+s+'`' for s in r['services'])} (see compose file).")
    if r["env_var_names"]:
        out.append(f"**Environment:** set {', '.join('`'+e+'`' for e in r['env_var_names'])} "
                   "(names only — see `.env.example`).")
    else:
        out.append("**Environment:** none declared.")
    if r["migration_dirs"] or r["setup_targets"]:
        parts = []
        if r["setup_targets"]:
            parts.append("run " + " / ".join(f"`make {t}`" for t in r["setup_targets"]))
        if r["migration_dirs"]:
            parts.append(f"migrations in `{r['migration_dirs'][0]}`")
        out.append(f"**First-run state:** {'; '.join(parts)}.")

    cmds = []
    if r["install_cmd"]:
        cmds.append(f"```\n{r['install_cmd']}\n```")
    if r["run_cmd"]:
        cmds.append(f"Run: `{r['run_cmd']}`")
    if r["test_cmd"]:
        cmds.append(f"Test: `{r['test_cmd']}`")
    out.append("\n\n".join(cmds) if cmds else _flag("no install/run/test command found in manifests, Makefile, or CI"))

    gaps = [g for g in f["clone_gaps"] if any(x in g["path"] for x in ("ops", "run", "make", "build"))]
    if gaps:
        out.append(_flag("regenerate/build from a clone: the docs reference "
                         + ", ".join(f"`{g['path']}`" for g in gaps[:3])
                         + " which is " + gaps[0]["why"] + " — ask a maintainer."))
    sib = f["sibling_repos"]
    if sib:
        out.append(f"**Sibling repos:** some processes need `{', '.join('../'+s for s in sib)}` checked out alongside.")

    extra = _authored(records, "run-it", fallback="")
    if extra:
        out += ["", extra]
    return "\n\n".join(x for x in out if x is not None)


def sec_codemap(f: dict, records: dict, exposure: str) -> str:
    s = f["structure"]
    out = []
    # §16b architecture sketch (draw agent) if present. §16a Mermaid module graph
    # is deferred until it can show real dependency edges — a nodes-only flowchart
    # isn't worth the space.
    if (Path(f["_repo_path"]) / "assets/onboarding/architecture-sketch.svg").exists() or \
       records.get("_has_sketch"):
        out.append("![Architecture sketch](assets/onboarding/architecture-sketch.svg)\n")
    authored_map = _authored(records, "codemap", fallback="")
    if authored_map:
        out.append(authored_map)
    else:
        rows = [[f"`{m}/`", "<!-- what it does: authored -->", ""] for m in s["modules"][:12]]
        out.append(_md_table(["module", "what it does", "grep for"], rows))
        out.append(_flag("per-module descriptions are authored — run `python3 -m author`"))
    return "\n\n".join(out)


def sec_landmines(f: dict, records: dict, exposure: str) -> str:
    inv, hist = f["invariants"], f["history"]
    items: list[str] = []
    for rule in inv["boundary_rules"]:
        items.append(f"- **{rule}** *(source: lint config — verified)*")
    for gp in inv["go_internal_pkgs"]:
        items.append(f"- `{gp}` is a Go internal package — not importable outside its parent *(verified)*")

    authored = _authored(records, "landmines", fallback="")
    if authored and authored != "None extracted.":
        if items:
            items.append("")
        items.append(authored)

    # history flags are weak signal — a footnote, and only if nothing stronger
    flags = hist["revert_commits"][:3]
    if flags and not authored:
        items.append("")
        items.append("_git history also flags (verify relevance):_ "
                     + "; ".join(f"`{x.split(chr(32))[0]}`" for x in flags))

    if not items:
        srcs = "lint configs, revert history, review comments, agent docs"
        return f"None extracted. Sources checked: {srcs}."

    if exposure == "public":
        items.append("")
        items.append("*(Rendered for a public surface — `exploitable` and `private-ref` "
                     "landmines are held to a maintainer-only report; see spec §15.)*")
    return "\n".join(items)


def sec_pr_gates(f: dict) -> str:
    c = f["contrib"]
    lines = []
    if f["activity"]["ci_present"]:
        lines.append(f"- CI must pass — `.github/workflows/`: {', '.join(f['activity']['ci_workflows'])}.")
    if c["dco"]:
        lines.append("- Commits must be signed off (`git commit -s`) — DCO observed in recent history.")
    if c["cla"]:
        lines.append("- A CLA check is configured.")
    if c["commit_convention"]:
        lines.append(f"- Commit-message convention: {c['commit_convention']}.")
    if c["pr_template_fields"]:
        lines.append("- PR template requires: " + ", ".join(c["pr_template_fields"]) + ".")
    not_found = []
    for label, val in (("CLA/DCO", c["dco"] or c["cla"]),
                       ("a commit convention", c["commit_convention"]),
                       ("a PR template", c["pr_template_fields"])):
        if not val:
            not_found.append(label)
    if not_found:
        lines.append(f"\nNot found (so not required): {', '.join(not_found)}.")
    if c["branch_rules"] is None:
        lines.append(_flag("branch-protection rules and required status checks are GitHub-only — not read offline"))
    return "\n".join(lines) if lines else _flag("no contribution gates found in config")


def sec_verify(f: dict, records: dict) -> str:
    r = f["run"]
    out = []
    if r["test_cmd"]:
        out.append(f"```\n{r['test_cmd']}\n```")
        out.append("\"Green\" = 0 failures.")
    else:
        out.append(_flag("no test command found — ask a maintainer how a change is checked"))
    if r["lint_cmd"]:
        out.append(f"Lint: `{r['lint_cmd']}`.")
    if r["needs_node_binary"]:
        out.append("`node` must be on `PATH` — some tests shell out to it.")
    extra = _authored(records, "verify", fallback="")
    if extra:
        out += ["", extra]
    return "\n\n".join(out)


def sec_pointers(f: dict) -> str:
    d, out = f["docs"], []
    if d["has_architecture_md"]:
        out.append("- `ARCHITECTURE.md` — the codemap and landmines")
    if d["has_contributing_md"]:
        out.append("- `CONTRIBUTING.md` — how to get a PR merged")
    if d["spec_dir"]:
        out.append("- `spec/` — internal contracts")
    for ad in d["agent_docs"]:
        out.append(f"- `{ad}` — operating rules (and the best landmine source)")
    for dd in d["doc_dirs"]:
        out.append(f"- `{dd}/` — deeper docs")
    for g in f["clone_gaps"]:
        if g["why"] == "gitignored":
            out.append(f"- `{g['path']}` — referenced in {g['in']} but **gitignored, not in a clone**")
    return "\n".join(out) if out else _flag("no secondary docs found")


# ── assembly ─────────────────────────────────────────────────────────────────
def _clean(md: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"


def _splice(existing: str, name: str, body: str) -> str:
    b, e = BEGIN.format(name), END.format(name)
    block = f"{b}\n{body}\n{e}"
    if b in existing and e in existing:
        return re.sub(re.escape(b) + r".*?" + re.escape(e), lambda _: block, existing, flags=re.S)
    return (existing.rstrip() + "\n\n" + block + "\n") if existing.strip() else block + "\n"


FILES = {
    "README.md": ["what-it-is", "maturity", "orientation", "run-it", "pointers"],
    "ARCHITECTURE.md": ["codemap", "landmines"],
    "CONTRIBUTING.md": ["first-contribution", "pr-gates", "verify"],
}
HEADERS = {"README.md": "# {name}", "ARCHITECTURE.md": "# Architecture", "CONTRIBUTING.md": "# Contributing"}


def render(facts: dict, authored: dict | None = None, *, exposure: str = "internal",
           fresh: bool = False) -> dict[str, str]:
    authored = authored or {}
    bodies = {
        "what-it-is": _authored(authored, "what-it-is"),
        "maturity": sec_maturity(facts),
        "orientation": _authored(authored, "orientation"),
        "run-it": sec_run_it(facts, authored),
        "pointers": sec_pointers(facts),
        "codemap": sec_codemap(facts, authored, exposure),
        "landmines": sec_landmines(facts, authored, exposure),
        "first-contribution": _authored(authored, "first-contribution"),
        "pr-gates": sec_pr_gates(facts),
        "verify": sec_verify(facts, authored),
    }
    repo_root = Path(facts["_repo_path"])
    out: dict[str, str] = {}
    for fname, sections in FILES.items():
        p = repo_root / fname
        if not fresh and p.is_file():
            existing = p.read_text(errors="replace")
        else:
            existing = HEADERS[fname].format(name=facts["repo"]["name"]) + "\n"
        doc = existing
        for s in sections:
            doc = _splice(doc, s, bodies[s])
        out[fname] = _clean(doc)
    return out


