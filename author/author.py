"""author.py — the single governed LLM call (spec §10).

Input:  facts.json + the repo's agent docs / README / a code digest.
Output: {section_name: body_md} for the authored + hybrid sections only.
        render.py slots these into the marker blocks.

Rules enforced in the prompt AND checked on the way out:
  - write only from what's provided; a null/absent fact -> the section's
    gap-flag string, never a guess
  - one Diátaxis mode per section
  - reference code by symbol name, never line numbers
  - landmines ONLY from facts.invariants + facts.history + agent-doc prose;
    if none -> the "none extracted" string. No generic engineering advice.
  - British English, plain, short sentences

    python3 -m author facts.json --out authored.json
    python3 -m author facts.json --model gemini-3.8-flash --exposure public
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from author import vendor_vertex_rest as vx

AUTHORED_SECTIONS = {
    "what-it-is":        "explanation — one paragraph: what this repo is, who it's for. No feature list.",
    "orientation":       "explanation — the one mental model a newcomer must hold, and (one line) why the project exists. Not how-to.",
    "run-it":            "tutorial — AT MOST two sentences, and only if the machine facts genuinely miss something: a non-obvious prerequisite, an ordering gotcha, or what 'it worked' looks like. Do NOT restate the install/test commands or the sibling-repo note — those are already rendered. Nothing to add → empty string.",
    "codemap":           "reference — a markdown table: | module | what it does | grep for |. One row per module in facts.structure.modules, in the order given (already ranked by real size/importance — don't re-sort). 'grep for' names a symbol UNIQUE TO THAT MODULE that a reader would actually search for — e.g. its most distinctive class/function name, not a generic one every module happens to share (a module whose only distinguishing entrypoint is a generic name like `main` gets grep text describing what to look for inside it instead, never the same bare word repeated across rows). No prose around it.",
    "landmines":         "explanation — a JSON ARRAY of records, one per real landmine. Each: {statement, source, class}. `statement` = one sentence, what bites someone changing this code (British English, plain). `source` = 'CLAUDE.md' | 'AGENTS.md' | 'lint config' | 'git history'. `class` = 'operational' (fragility the team already documents — deploy≠reachable, stop-after-two-failures), 'exploitable' (describes a silent failure, a bypass, an unguarded gap), or 'private-ref' (names a private repo, a credential path, a gitignored file, or a hidden internal tier). ONLY from the invariant rules, history flags, and agent-doc prose provided. Nothing real → an empty array [].",
    "first-contribution":"how-to — a scoped first change with a clear definition of done, from the starter issues or (if none) the smallest recent changes. Don't invent scope.",
    "verify":            "how-to — ONLY what the test command alone doesn't convey: which checks matter, what a specific failure means. If nothing to add, empty string.",
}

_SYSTEM = """You write contributor onboarding documentation. You are given a
facts object and some of a repository's own text. Produce a JSON object mapping
each requested section name to its markdown body.

HARD RULES — a violation makes the output worse than nothing:
- Use ONLY the facts and text provided. If a value you'd need is null or absent,
  write the section's stated gap-flag (or an empty string where allowed) — never
  guess, never write "probably".
- No generic software-engineering advice. Every sentence is about THIS repo.
- Reference code by symbol name for grep ("grep `class SketchExecutor`"), never
  "file.py:214".
- Landmines come only from the invariant rules, the history flags, and the
  agent-doc prose given. Each landmine ends with *(source: CLAUDE.md)* etc. If
  there is nothing real, the whole section is exactly: None extracted.
- British English. Plain language. Short sentences. One Diátaxis mode per section
  (stated per section).
{exposure_rule}

Return ONLY the JSON object. Keys: {keys}."""

_EXPOSURE_PUBLIC = """- EXPOSURE = public. In EVERY section: never name a private
  repo, a credential path, a gitignored file, or a hidden internal tier —
  generalise to "a private/internal path" or "a private sibling repo". In
  landmines: still classify each record honestly (the render step drops the
  non-operational ones); write operational ones already generalised."""


def build_digest(repo: Path, facts: dict, *, max_doc=14000) -> str:
    """The repo-text half of the prompt: agent docs / README + a thin
    structure digest. Public (not `_digest`) because `serve` needs it too —
    the server has no local checkout, so a caller who wants a real `author`
    call over A2A must compute this locally (where the checkout actually is)
    and send the resulting string, not a repo path."""
    parts = []
    for name in facts["docs"]["agent_docs"] + (["README.md"] if not facts["docs"]["agent_docs"] else []):
        p = repo / name
        if p.is_file():
            parts.append(f"### {name}\n{p.read_text(errors='replace')[:max_doc]}")
    # a thin code digest: entrypoints + a few most-churned dirs' file lists
    parts.append("### structure\n" + json.dumps({
        "modules": facts["structure"]["modules"],
        "entrypoints": facts["structure"]["entrypoints"],
        "top_dirs": list(facts["structure"]["top_dirs"])[:20],
    }, indent=1))
    return "\n\n".join(parts)


def build_authored(facts: dict, *, model="gemini-3.8-flash", exposure="internal",
                   digest: str | None = None, timeout=120) -> dict:
    """`digest`: pass the repo-text digest explicitly when there's no local
    checkout to read it from (e.g. `serve`, which only ever receives
    facts.json + a digest string over A2A — never a repo path). Left as
    `None` (the CLI's own default), this reads it from
    `facts["_repo_path"]` locally, unchanged from before `serve` existed. A
    repo_path that doesn't exist locally (or isn't a directory) degrades to
    an empty digest rather than raising — an honest "less context available",
    the same anti-fabrication posture the rest of this module already takes
    for a missing fact, not a hard failure."""
    repo = Path(facts["_repo_path"])
    if digest is None:
        digest = build_digest(repo, facts) if repo.is_dir() else ""
    keys = list(AUTHORED_SECTIONS)
    section_brief = "\n".join(f"- {k}: {v}" for k, v in AUTHORED_SECTIONS.items())
    gap_flags = {
        "run-it": "", "verify": "",
        "codemap": "(module list unavailable)",
        "landmines": "[]",
        "what-it-is": "> UNKNOWN — no description available",
        "orientation": "> UNKNOWN — no design docs to summarise",
        "first-contribution": "> UNKNOWN — no starter issues and no recent small changes",
    }

    user = (
        f"FACTS:\n{json.dumps(facts, indent=1)[:20000]}\n\n"
        f"REPO TEXT:\n{digest}\n\n"
        f"SECTIONS TO WRITE (name: mode + instruction):\n{section_brief}\n\n"
        f"GAP-FLAG per section when you can't write it truthfully:\n{json.dumps(gap_flags, indent=1)}"
    )
    system = _SYSTEM.format(
        keys=", ".join(keys),
        exposure_rule=_EXPOSURE_PUBLIC if exposure == "public" else "- EXPOSURE = internal (full candour).",
    )
    schema = {
        "type": "OBJECT",
        "properties": {
            k: ({"type": "ARRAY", "items": {
                    "type": "OBJECT",
                    "properties": {"statement": {"type": "STRING"},
                                   "source": {"type": "STRING"},
                                   "class": {"type": "STRING",
                                             "enum": ["operational", "exploitable", "private-ref"]}},
                    "required": ["statement", "source", "class"]}}
                 if k == "landmines" else {"type": "STRING"})
            for k in keys
        },
        "required": keys,
    }
    resp = vx.call(model, [{"role": "user", "parts": [{"text": user}]}],
                   system=system, schema=schema, temperature=0.2,
                   max_output_tokens=16000, timeout=timeout)
    text = (vx.first_part(resp) or {}).get("text", "")
    try:
        out = json.loads(text)
    except json.JSONDecodeError as e:
        raise SystemExit(f"author: model reply was not JSON ({e}): {text[:300]}")

    # on-the-way-out checks
    warnings = []
    for k, v in out.items():
        if isinstance(v, str) and re.search(r"\b\w+\.\w+:\d+", v):
            warnings.append(f"{k}: contains a file:line reference")
    lm = out.get("landmines")
    if isinstance(lm, list):
        for i, r in enumerate(lm):
            if not isinstance(r, dict) or {"statement", "source", "class"} - set(r):
                warnings.append(f"landmines[{i}]: missing statement/source/class")
        held = [r for r in lm if isinstance(r, dict)
                and r.get("class") in ("exploitable", "private-ref")]
        if exposure == "public" and held:
            warnings.append(f"landmines: {len(held)} record(s) "
                            "will be moved to MAINTAINER-NOTES.md by render (public)")
    return {"_model": model, "_exposure": exposure, "_warnings": warnings, **out}
