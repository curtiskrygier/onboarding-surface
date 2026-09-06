"""review.py — a static HITL review page for one onboarding run.

Read-only preview: what render produced, what a maintainer must check, and
the diff against the repo's current docs. No approve/reject here — that's
the --pr gate. SVG sketch renders inline; no JS libraries.

    python3 -m review --facts facts.json --docs onboarded/x/docs --repo /path/to/x --out review.html
"""
from __future__ import annotations

import argparse
import difflib
import html
import json
import re
from datetime import date
from pathlib import Path

import markdown as md

from render.render import BEGIN, END, _splice

KIND = {
    "what-it-is": "authored", "maturity": "deterministic", "orientation": "authored",
    "run-it": "hybrid", "pointers": "deterministic", "codemap": "hybrid",
    "landmines": "hybrid", "first-contribution": "hybrid", "pr-gates": "deterministic",
    "verify": "hybrid",
}
FILE_SECTIONS = {
    "README.md": ["what-it-is", "maturity", "orientation", "run-it", "pointers"],
    "ARCHITECTURE.md": ["codemap", "landmines"],
    "CONTRIBUTING.md": ["first-contribution", "pr-gates", "verify"],
}
_UNKNOWN = re.compile(r"^> \*\*UNKNOWN\*\* — (.+)$", re.M)
_PENDING = re.compile(r"authored:\s*pending")


def _block(doc: str, name: str) -> str | None:
    m = re.search(re.escape(BEGIN.format(name)) + r"\n(.*?)\n" + re.escape(END.format(name)), doc, re.S)
    return m.group(1) if m else None


def _assess(body: str, name: str) -> dict:
    flags = []
    n_unknown = len(_UNKNOWN.findall(body))
    if n_unknown:
        flags.append(f"{n_unknown} UNKNOWN")
    if _PENDING.search(body):
        flags.append("authored pending")
    kind = KIND.get(name, "hybrid")
    conf = "verified" if kind == "deterministic" else "inferred"
    if _PENDING.search(body) or (body.strip().startswith("> **UNKNOWN**") and n_unknown):
        conf = "unknown"
    return {"kind": kind, "confidence": conf, "flags": flags, "n_unknown": n_unknown}


_MD = md.Markdown(extensions=["tables", "fenced_code", "sane_lists"])


def _render_md(text: str) -> str:
    _MD.reset()
    return _MD.convert(text)


CSS = """
:root{--bg:#fbfcfd;--panel:#f4f6f9;--ink:#1e293b;--muted:#64748b;--line:#d7dee7;
--accent:#2563eb;--ok:#16a34a;--warn:#b45309;--gap:#dc2626;
--mono:"SF Mono",ui-monospace,Menlo,monospace;--sans:ui-sans-serif,system-ui,-apple-system,sans-serif;}
@media(prefers-color-scheme:dark){:root{--bg:#0d1420;--panel:#151e2c;--ink:#e5eaf1;
--muted:#93a2b6;--line:#28344699;--accent:#5b8bf5;}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 var(--sans)}
.wrap{max-width:940px;margin:0 auto;padding:48px 28px 80px}
h1{font-size:22px;margin:0 0 4px}.sub{color:var(--muted);margin:0 0 28px;font-size:14px}
.sub code{font-family:var(--mono);font-size:.85em}
.bar{display:flex;gap:14px;margin:0 0 28px;flex-wrap:wrap}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 16px;flex:1;min-width:150px}
.stat b{display:block;font-size:22px;font-family:var(--mono)}.stat span{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.06em}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:36px 0 12px;font-family:var(--mono)}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.05em}
.pill{font-family:var(--mono);font-size:11px;padding:2px 7px;border-radius:5px;border:1px solid var(--line)}
.k-authored{color:var(--accent);border-color:var(--accent)}
.k-deterministic{color:var(--muted)}
.c-unknown,.f{color:var(--gap)}.c-inferred{color:var(--warn)}.c-verified{color:var(--ok)}
ul.gaps{padding-left:0;list-style:none}ul.gaps li{padding:8px 12px;border-left:3px solid var(--gap);background:var(--panel);margin-bottom:6px;border-radius:0 6px 6px 0}
ul.gaps code{font-family:var(--mono);font-size:.85em}
.sketch{border:1px solid var(--line);border-radius:10px;padding:20px;background:#fff;text-align:center}
.sketch svg{max-width:100%;height:auto}
details{border:1px solid var(--line);border-radius:10px;margin:14px 0;background:var(--panel)}
details>summary{cursor:pointer;padding:12px 16px;font-weight:600;font-family:var(--mono);font-size:13px}
.doc{padding:4px 22px 18px;border-top:1px solid var(--line)}
.doc h1{font-size:20px}.doc h2{font-family:var(--sans);text-transform:none;letter-spacing:0;color:var(--ink);font-size:17px}
.doc table{font-size:13.5px}.doc code{font-family:var(--mono);font-size:.86em;background:var(--panel);padding:1px 4px;border-radius:3px}
.doc pre{background:#0d1420;color:#e5eaf1;padding:12px 14px;border-radius:8px;overflow-x:auto}
.doc pre code{background:none;color:inherit}
.doc blockquote{border-left:3px solid var(--gap);margin:0;padding:2px 14px;color:var(--gap)}
.diff{padding:0 22px 18px;border-top:1px solid var(--line)}
.diff pre{font-family:var(--mono);font-size:12px;line-height:1.5;overflow-x:auto;margin:8px 0}
.diff .a{color:var(--ok)}.diff .d{color:var(--gap)}.diff .h{color:var(--muted)}
"""


def build(facts: dict, docs_dir: Path, repo: Path) -> str:
    name = facts["repo"]["name"]
    rows, gaps = [], []
    proposed: dict[str, str] = {}
    for fname, sections in FILE_SECTIONS.items():
        prop = (docs_dir / fname).read_text() if (docs_dir / fname).is_file() else ""
        proposed[fname] = prop
        for s in sections:
            body = _block(prop, s)
            if body is None:
                rows.append((s, fname, "—", "missing", ["not rendered"]))
                continue
            a = _assess(body, s)
            rows.append((s, fname, a["kind"], a["confidence"], a["flags"]))
            for g in _UNKNOWN.findall(body):
                gaps.append((s, fname, g))

    n_auth = sum(1 for r in rows if r[2] == "authored")
    n_hyb = sum(1 for r in rows if r[2] == "hybrid")

    # diffs vs current
    diffs = {}
    for fname, prop in proposed.items():
        cur = (repo / fname).read_text(errors="replace") if (repo / fname).is_file() else ""
        spliced = cur or f"# {name}\n"
        for s in FILE_SECTIONS[fname]:
            b = _block(prop, s)
            if b is not None:
                spliced = _splice(spliced, s, b)
        d = list(difflib.unified_diff(cur.splitlines(), spliced.splitlines(),
                                      "current", "proposed", lineterm=""))
        diffs[fname] = d

    sketch_svg = ""
    for c in (repo / "assets/onboarding/architecture-sketch.svg",
              docs_dir.parent / "architecture-sketch.svg"):
        if c.is_file():
            sketch_svg = c.read_text()
            break

    def esc(s): return html.escape(str(s))

    row_html = "\n".join(
        f"<tr><td><code>{esc(s)}</code></td><td>{esc(f)}</td>"
        f"<td><span class='pill k-{esc(k)}'>{esc(k)}</span></td>"
        f"<td class='c-{esc(c)}'>{esc(c)}</td>"
        f"<td class='f'>{esc(', '.join(fl)) if fl else '—'}</td></tr>"
        for s, f, k, c, fl in rows)

    gaps_html = ("<ul class='gaps'>" + "".join(
        f"<li><code>{esc(s)}</code> · {esc(f)} — {esc(g)}</li>" for s, f, g in gaps
    ) + "</ul>") if gaps else "<p style='color:var(--muted)'>None — every fact resolved.</p>"

    def diff_html(d):
        if not d:
            return "<p style='color:var(--muted)'>No change.</p>"
        out = []
        for ln in d:
            cls = "a" if ln.startswith("+") else "d" if ln.startswith("-") else "h" if ln.startswith("@") else ""
            out.append(f"<span class='{cls}'>{esc(ln)}</span>")
        return "<pre>" + "\n".join(out) + "</pre>"

    docs_html = "\n".join(
        f"<details open><summary>{esc(fn)}</summary>"
        f"<div class='doc'>{_render_md(proposed[fn])}</div>"
        f"<div class='diff'><b>diff vs current</b>{diff_html(diffs[fn])}</div></details>"
        for fn in FILE_SECTIONS)

    return f"""<!doctype html><meta charset=utf-8>
<title>Onboarding review — {esc(name)}</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<style>{CSS}</style>
<div class=wrap>
<h1>{esc(name)} — onboarding surface review</h1>
<p class=sub>generated {date.today().isoformat()} ·
model <code>{esc(facts.get('_authored_model','—'))}</code> ·
exposure <code>{esc(facts.get('_exposure','internal'))}</code> ·
repo_kind <code>{esc(facts['repo_kind'])}</code></p>

<div class=bar>
<div class=stat><b>{len(rows)}</b><span>sections</span></div>
<div class=stat><b class=k-authored>{n_auth}+{n_hyb}</b><span>authored + hybrid — read these</span></div>
<div class=stat><b class=f>{len(gaps)}</b><span>UNKNOWNs — check these</span></div>
<div class=stat><b>{len(facts['clone_gaps'])}</b><span>clone gaps</span></div>
</div>

<h2>Sections</h2>
<table><tr><th>section</th><th>file</th><th>kind</th><th>confidence</th><th>flags</th></tr>
{row_html}</table>

<h2>The gaps to check</h2>
{gaps_html}

{"<h2>Architecture sketch</h2><div class=sketch>" + sketch_svg + "</div>" if sketch_svg else ""}

<h2>The docs</h2>
{docs_html}
</div>"""
