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


def _authored(records: dict, name: str, *, fallback: str | None = None) -> str:
    body = (records or {}).get(name)
    if body:
        return body.strip()
    # fallback="" is a deliberate "render nothing" (the model had nothing to add);
    # only fall through to the pending marker when no fallback was given at all.
    return fallback if fallback is not None else "<!-- authored: pending — run `python3 -m author` -->"


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


_PRIVATE_HINT = re.compile(r"(^|/)(ops|private|internal|secret|\.clasp|clasprc)", re.I)


def sec_run_it(f: dict, records: dict, exposure: str = "internal"):
    """Returns (body_md, maint_notes[]). In public mode a build/regen gap that is
    purely private tooling is NOT flagged in the doc — a public contributor
    building with the shown commands doesn't need an 'ask a maintainer about the
    hidden flow' caveat (the sibling-repos line already carries that signal). It
    goes to MAINTAINER-NOTES.md instead (spec §15)."""
    r, kind = f["run"], f["repo_kind"]
    out, maint = [], []
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
        if exposure == "public":
            priv = [g for g in gaps if _PRIVATE_HINT.search(g["path"])]
            pub = [g for g in gaps if not _PRIVATE_HINT.search(g["path"])]
            if pub:
                out.append(_flag("regenerate/build from a clone: the docs reference "
                                 + ", ".join(f"`{g['path']}`" for g in pub[:3])
                                 + " which is " + pub[0]["why"] + " — ask a maintainer."))
            if priv:
                maint.append("run-it: the docs reference build/regeneration tooling ("
                             + ", ".join(f"`{g['path']}`" for g in priv[:3])
                             + ") not in a public clone — omitted from the public run-it section.")
        else:
            out.append(_flag("regenerate/build from a clone: the docs reference "
                             + ", ".join(f"`{g['path']}`" for g in gaps[:3])
                             + " which is " + gaps[0]["why"] + " — ask a maintainer."))
    sib = f["sibling_repos"]
    if sib:
        if exposure == "public":
            out.append("**Sibling repos:** some processes need a private sibling repo "
                       "checked out alongside — ask a maintainer.")
        else:
            out.append(f"**Sibling repos:** some processes need `{', '.join('../'+s for s in sib)}` checked out alongside.")

    extra = _authored(records, "run-it", fallback="")
    if extra:
        out += ["", extra]
    return "\n\n".join(x for x in out if x is not None), maint


def _strip_private_table_rows(md: str, toks: set[str]) -> tuple[str, list[str]]:
    """Public mode: drop a whole markdown table row whose cells name a private
    token. A row is structured — dropping it is not the char-level prose
    mangling that was tried and reverted. Header/separator rows are kept."""
    kept, dropped = [], []
    for ln in md.splitlines():
        s = ln.strip()
        is_row = s.startswith("|") and not re.match(r"\|[\s:|-]+\|?\s*$", s)
        if is_row and _hits_private(ln, toks):
            dropped.append(re.sub(r"\s+", " ", s)[:120])
            continue
        kept.append(ln)
    return "\n".join(kept), dropped


def sec_codemap(f: dict, records: dict, exposure: str):
    """Returns (body_md, maint_notes[])."""
    s = f["structure"]
    out, maint = [], []
    # §16b architecture sketch (draw agent) if present. §16a Mermaid module graph
    # is deferred until it can show real dependency edges — a nodes-only flowchart
    # isn't worth the space.
    if (Path(f["_repo_path"]) / "assets/onboarding/architecture-sketch.svg").exists() or \
       records.get("_has_sketch"):
        out.append("![Architecture sketch](assets/onboarding/architecture-sketch.svg)\n")
    authored_map = _authored(records, "codemap", fallback="")
    if authored_map:
        if exposure == "public":
            authored_map, dropped = _strip_private_table_rows(authored_map, _private_tokens(f))
            maint += [f"codemap: dropped a table row naming private tooling — `{d}`"
                      for d in dropped]
        out.append(authored_map)
    else:
        rows = [[f"`{m}/`", "<!-- what it does: authored -->", ""] for m in s["modules"][:12]]
        out.append(_md_table(["module", "what it does", "grep for"], rows))
        out.append(_flag("per-module descriptions are authored — run `python3 -m author`"))
    return "\n\n".join(out), maint


def _landmine_records(records: dict) -> list[dict]:
    """Normalise: classified array (current author) or a legacy markdown string
    (hand-written authored.json) -> [{statement, source, class}]."""
    lm = (records or {}).get("landmines")
    if isinstance(lm, list):
        return [r for r in lm if isinstance(r, dict) and r.get("statement")]
    if isinstance(lm, str) and lm.strip() and lm.strip() != "None extracted.":
        out = []
        for line in lm.splitlines():
            line = re.sub(r"^\s*[-*+]\s+", "", line.rstrip()).strip()  # one bullet marker only
            if not line:
                continue
            # trailing *(...)* is the source cite — with or without a "source:" prefix
            m = re.search(r"\*\(\s*(?:source:\s*)?([^)]+?)\s*\)\*\s*$", line)
            src = m.group(1).strip() if m else "authored"
            stmt = line[:m.start()].rstrip(" .") if m else line
            out.append({"statement": stmt, "source": src, "class": "operational"})
        return out
    return []


def _private_tokens(facts: dict) -> set[str]:
    toks = {g["path"] for g in facts["clone_gaps"] if g["why"] == "gitignored"}
    toks |= set(facts["sibling_repos"])
    toks |= {"Code.private", ".clasp.json", "clasprc", "ops/ops.py", "ops.py",
             "mcp-worker", "A2UIState", "a2uithoughts"}
    return {t for t in toks if t}


# Structural private-content signals that name nothing in the token set
# (Gemini 3.8 review: paraphrase and syntax escape a literal match). Kept
# deliberately tight — a hit means "a human should look", it does not rewrite.
_PRIVATE_RE = [
    re.compile(r"\b[A-Z][A-Z0-9]{2,}_(?:KEY|SECRET|TOKEN|PASSWORD|PASS|AUTH|CRED|CREDENTIALS)\b"),
    re.compile(r"\b(?:https?://)?[a-z0-9.-]+\.(?:internal|corp|local|intranet)\b", re.I),
    re.compile(r"\b(?:10|127)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


def _hits_private(text: str, toks: set[str]) -> bool:
    if any(re.search(r"(^|[\s`(/])" + re.escape(t) + r"($|[\s`).,/])", text) for t in toks):
        return True
    return any(rx.search(text) for rx in _PRIVATE_RE)


def _reclassify_private(recs: list[dict], toks: set[str]) -> list[dict]:
    """Deterministic safety net (spec §15): a record the model called
    'operational' but whose statement still names a private path (or matches a
    structural credential/internal-host signal) is forced to 'private-ref' so
    the public render filter holds it back regardless of the model's call.
    Legacy string landmines (all 'operational') pass through here too."""
    for r in recs:
        if r.get("class") != "operational":
            continue
        if _hits_private(r.get("statement", ""), toks):
            r["class"] = "private-ref"
    return recs


def sec_landmines(f: dict, records: dict, exposure: str):
    """Returns (body_md, maintainer_records[]). In public mode, exploitable and
    private-ref records are dropped from the body and returned separately for
    MAINTAINER-NOTES.md (spec §15)."""
    inv = f["invariants"]
    det: list[dict] = []
    for rule in inv["boundary_rules"]:
        det.append({"statement": rule, "source": "lint config", "class": "operational"})
    for gp in inv["go_internal_pkgs"]:
        det.append({"statement": f"`{gp}` is a Go internal package — not importable outside its parent",
                    "source": "verified", "class": "operational"})

    recs = det + _landmine_records(records)
    # the model sometimes bakes the *(source: X)* suffix into `statement` despite
    # the schema — strip it so the renderers don't double it up.
    for r in recs:
        r["statement"] = re.sub(r"\.?\s*\*\(source:[^)]*\)\*\.?\s*$", "",
                                r.get("statement", "")).strip()

    held: list[dict] = []
    if exposure == "public":
        recs = _reclassify_private(recs, _private_tokens(f))
        kept = [r for r in recs if r["class"] == "operational"]
        held = [r for r in recs if r["class"] != "operational"]
        recs = kept

    # No count, no class names in the public footnote: telling a reader "3
    # landmines held back" advertises exactly what to go looking for
    # (Gemini 3.8 review — the Streisand footnote). Just point maintainers at
    # their own file.
    held_note = "*Some maintainer-only notes for this repo are kept out of the public docs.*"

    if not recs:
        base = "None extracted. Sources checked: lint configs, revert history, review comments, agent docs."
        if held:
            base += "\n\n" + held_note
        return base, held

    lines = [f"- {r['statement'].rstrip('.')}. *(source: {r['source']})*" for r in recs]
    if held:
        lines += ["", held_note]
    return "\n".join(lines), held


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


def sec_pointers(f: dict, exposure: str = "internal") -> str:
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
    ignored = [g for g in f["clone_gaps"] if g["why"] == "gitignored"]
    if ignored:
        # a gitignored path IS the private signal — in public mode never name them.
        if exposure == "public":
            out.append("- Some docs referenced internally are not in the public clone.")
        else:
            for g in ignored:
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


def _leak_scan(bodies: dict, facts: dict) -> list[str]:
    """Public-mode residual-leak check: an authored section body still naming a
    private path the author was told to generalise. Flags for the human — never
    mangles the text."""
    toks = _private_tokens(facts)
    hits = []
    for name in ("what-it-is", "orientation", "run-it", "first-contribution", "codemap"):
        b = bodies.get(name, "")
        b = b if isinstance(b, str) else ""
        for t in toks:
            if t and re.search(r"(^|[\s`(/])" + re.escape(t) + r"($|[\s`).,/])", b):
                hits.append(f"{name}: still names `{t}` — generalise before publishing")
        for rx in _PRIVATE_RE:
            for m in rx.findall(b):
                hits.append(f"{name}: matches a private-content pattern (`{m}`) — check before publishing")
    return sorted(set(hits))


def render(facts: dict, authored: dict | None = None, *, exposure: str = "internal",
           fresh: bool = False) -> dict[str, str]:
    authored = authored or {}
    lm_body, lm_held = sec_landmines(facts, authored, exposure)
    run_body, run_maint = sec_run_it(facts, authored, exposure)
    cm_body, cm_maint = sec_codemap(facts, authored, exposure)
    bodies = {
        "what-it-is": _authored(authored, "what-it-is"),
        "maturity": sec_maturity(facts),
        "orientation": _authored(authored, "orientation"),
        "run-it": run_body,
        "pointers": sec_pointers(facts, exposure),
        "codemap": cm_body,
        "landmines": lm_body,
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

    if exposure == "public":
        leaks = _leak_scan(bodies, facts)
        parts = ["# Maintainer notes — not for the public surface\n"]
        if lm_held:
            parts.append("## Landmines held back (spec §15)\n")
            parts += [f"- **[{r['class']}]** {r['statement'].rstrip('.')}. *(source: {r['source']})*"
                      for r in lm_held]
            parts.append("")
        flow_maint = run_maint + cm_maint
        if flow_maint:
            parts.append("## Contributor-flow details kept out of the public docs\n")
            parts += [f"- {x}" for x in flow_maint]
            parts.append("")
        if leaks:
            parts.append("## Residual private references in authored prose — edit before publishing\n")
            parts += [f"- {x}" for x in leaks]
        if lm_held or flow_maint or leaks:
            out["MAINTAINER-NOTES.md"] = "\n".join(parts) + "\n"
    return out


