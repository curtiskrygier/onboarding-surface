"""draw.py — the architecture sketch (spec §16b): facts.json -> a structured
prompt -> one freeform_canvas-shaped LLM call -> a sanitised, cached SVG file.

An `authored` artifact — non-deterministic, cadence-only. NEVER wired into
`extract`/`render`'s own call chain; `onboard.py --art` (or a direct
`python3 -m draw`) is the only thing that invokes it. `render` already knows
how to embed the result (`sec_codemap` checks for
`<repo>/assets/onboarding/architecture-sketch.svg`, or an authored `_has_sketch`
flag) — draw.py's whole job is producing that file honestly.

    python3 -m draw facts.json                       # writes into the repo itself
    python3 -m draw facts.json --exposure public --out some/other/path.svg
    python3 -m draw facts.json --detail detailed --force   # ignore the cache

Honesty rule (matches §9's anti-fabrication line for prose): the box list, the
edge list and the zone grouping are built HERE, from facts.json only — real
module names, real services, real CI presence, real clone_gaps. The model gets
that structure and does layout; it never invents a relationship this repo's
facts don't support. `extract` doesn't do import/dependency analysis (§16a is
deferred for exactly that reason), so the edges drawn here are the ones facts
actually prove: containment (repo -> its modules), an entrypoint driving a
declared service, CI producing a declared generated-output dir, a contributor
needing a declared sibling repo. Nothing else.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from author import vendor_vertex_rest as vx
from render.render import _hits_private, _private_tokens

MODEL = "gemini-3.8-flash"
_ENTRY_ACCENT = "#2563eb"


# ── 1. box/edge/zone spec — built from facts only, no invention ────────────
def _generalise(label: str, toks: set[str]) -> str:
    return "a private/internal path" if _hits_private(label, toks) else label


def build_diagram_spec(facts: dict, *, exposure: str = "internal",
                       detail: str = "overview") -> dict:
    """Returns {"zones": [{id,title,direction}], "boxes": [{id,label,zone,accent}],
    "edges": [{from,to,label}]} — the ONLY inputs the draw agent's prompt is
    built from."""
    toks = _private_tokens(facts) if exposure == "public" else set()
    s, r, repo = facts["structure"], facts["run"], facts["repo"]
    total_cap = 10 if detail == "overview" else 16

    zones = [{"id": "codebase", "title": "CODEBASE", "direction": "top-down"}]
    boxes = [{"id": "root", "label": repo["name"], "zone": "codebase", "accent": True}]
    edges = []

    entries = s.get("entrypoints", [])[:2]
    has_runtime = bool(r.get("services")) and (facts["repo_kind"] == "service" or r.get("run_cmd"))
    has_build = facts["activity"]["ci_present"] and s.get("generated_file_count", 0) > 0
    priv_gaps = [g for g in facts["clone_gaps"]
                if re.search(r"(^|/)(ops|private|internal|secret)", g["path"], re.I)]
    has_private = bool(priv_gaps or facts["sibling_repos"])

    # reserve budget for everything that ISN'T a plain module box, so the
    # overview cap (spec §16b: <=10 boxes) bounds the TOTAL, not just modules
    reserved = 1 + len(entries) + (2 if has_build else 0) + (1 if has_private else 0)
    mod_budget = max(3, total_cap - reserved)

    for m in s["modules"][:mod_budget]:
        bid = f"mod:{m}"
        boxes.append({"id": bid, "label": m, "zone": "codebase"})
        edges.append({"from": "root", "to": bid, "label": ""})

    for e in entries:
        bid = f"entry:{e}"
        boxes.append({"id": bid, "label": e, "zone": "codebase"})
        edges.append({"from": bid, "to": "root", "label": "starts"})

    # runtime zone — only what run.services/run_cmd actually declare
    if has_runtime:
        zones.append({"id": "runtime", "title": "RUNTIME", "direction": "left-right"})
        boxes.append({"id": "svc:app", "label": r.get("run_cmd") or "the running app",
                     "zone": "runtime"})
        for svc in r["services"][:(4 if detail == "overview" else 6)]:
            bid = f"svc:{svc}"
            boxes.append({"id": bid, "label": _generalise(svc, toks), "zone": "runtime"})
            edges.append({"from": "svc:app", "to": bid, "label": "depends on"})

    # build zone — only if CI is real AND there's a real generated-output dir
    if has_build:
        zones.append({"id": "build", "title": "BUILD", "direction": "left-right"})
        ci_label = ", ".join(facts["activity"]["ci_workflows"][:2]) or "CI"
        boxes.append({"id": "ci", "label": ci_label, "zone": "build"})
        boxes.append({"id": "out", "label": f"generated output ({s['generated_file_count']} files)",
                     "zone": "build"})
        edges.append({"from": "ci", "to": "out", "label": "builds & deploys"})

    # private-tier annotation — only if clone_gaps/sibling_repos actually say so
    if has_private:
        label = ("a private/internal path" if exposure == "public"
                 else (priv_gaps[0]["path"] if priv_gaps else facts["sibling_repos"][0]))
        boxes.append({"id": "private", "label": label, "zone": "codebase"})
        edges.append({"from": "root", "to": "private", "label": "needs (not in a public clone)"})

    return {"zones": zones, "boxes": boxes, "edges": edges}


def _input_hash(spec: dict) -> str:
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:16]


# ── 2. the draw-agent call — freeform_canvas, svg mode, one shot ───────────
_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "STRING"},
        "justification": {"type": "STRING"},
        "svg": {"type": "STRING"},
    },
    "required": ["summary", "justification", "svg"],
}

_SYSTEM = """You draw one architecture-sketch diagram as a single raw SVG markup
string, using the freeform_canvas atom's rules. You are given a fixed box list,
edge list and zone grouping — draw exactly those, inventing no additional boxes,
edges or relationships. Your job is layout and visual clarity, not content.

Rules:
- Root element `<svg>`; viewBox="0 0 1100 700"; no width/height attrs on it.
- Every box from the input becomes one rounded <rect> + one centred <text> (wrap
  onto a <tspan> second line if the label is long) inside it. Boxes >= 160x64.
  Text >= 12px. A box needing more than 3 lines gets a bigger box, not smaller text.
- Draw each zone as its own horizontal band: a faint full-width background
  <rect> (very light fill, no stroke) behind that zone's boxes, plus a small
  uppercase band-title <text> in the band's top-left corner. Leave clear
  whitespace between bands — no dead space, but bands must not visually merge.
- Zone direction: "top-down" stacks that zone's boxes vertically with a
  downward arrow between each; "left-right" lays them out left to right with a
  rightward arrow between each.
- Every edge becomes one <line> or <path> with `marker-end="url(#arrow)"`
  (define one arrow <marker> in <defs>). If the edge has a non-empty label,
  place a small <text> beside its midpoint.
- The one box marked accent gets a distinct fill/stroke colour ({accent}); every
  other box is a neutral fill (#ffffff or #f8fafc) with a light stroke (#cbd5e1).
- No <script>, <foreignObject>, <image>, <iframe>, <object>, <embed>, no
  event-handler attributes, no external URLs, no <style> element.
- Do NOT draw a full-canvas background rect — the canvas is left transparent
  and the surface that embeds this SVG supplies its own background.
- Font: font-family="system-ui, -apple-system, sans-serif" throughout.

Return ONLY the JSON object: summary (plain text, for alt text), justification
(>= 20 characters), svg (the markup string, root element `<svg>...</svg>`)."""


class DrawError(RuntimeError):
    pass


def call_draw_agent(spec: dict, *, model: str = MODEL, timeout: int = 90) -> dict:
    prompt = ("ZONES:\n" + json.dumps(spec["zones"], indent=1) +
             "\n\nBOXES:\n" + json.dumps(spec["boxes"], indent=1) +
             "\n\nEDGES:\n" + json.dumps(spec["edges"], indent=1))
    try:
        resp = vx.call(model, [{"role": "user", "parts": [{"text": prompt}]}],
                       system=_SYSTEM.format(accent=_ENTRY_ACCENT),
                       schema=_SCHEMA, temperature=0.4, max_output_tokens=8000,
                       timeout=timeout)
        part = vx.first_part(resp)
    except Exception as e:  # noqa: BLE001 — surfaced as one DrawError, caller decides
        raise DrawError(f"draw agent call failed: {e}") from e
    text = (part or {}).get("text")
    if not text:
        raise DrawError("draw agent returned no text content")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise DrawError(f"draw agent reply was not JSON ({e}): {text[:200]}") from e


# ── 3. deterministic SVG post-processing (never trust raw model output) ────
_FORBIDDEN_TAGS = re.compile(
    r"<\s*(script|foreignObject|iframe|object|embed|image)\b.*?(?:/>|</\s*\1\s*>)",
    re.I | re.S)
_EVENT_ATTR = re.compile(r'\s+on\w+\s*=\s*"[^"]*"', re.I)
_STYLE_TAG = re.compile(r"<\s*style\b.*?</\s*style\s*>", re.I | re.S)
_BAD_URL_ATTR = re.compile(
    r'\s+(href|xlink:href)\s*=\s*"(?!#)[^"]*"', re.I)
# a full-canvas background rect the model drew anyway despite being told not to
_BG_RECT = re.compile(
    r'<rect\b[^>]*\bwidth\s*=\s*"(?:100%|1100)"[^>]*\bheight\s*=\s*"(?:100%|700)"[^>]*/>\s*',
    re.I)


def sanitise_svg(svg: str) -> str:
    """Strip anything dangerous in an embedded static asset, and the baked
    full-canvas background the prompt already forbids. Never rewrites content,
    only removes — same "flag, don't mangle" discipline as render's leak scan."""
    svg = _FORBIDDEN_TAGS.sub("", svg)
    svg = _STYLE_TAG.sub("", svg)
    svg = _EVENT_ATTR.sub("", svg)
    svg = _BAD_URL_ATTR.sub("", svg)
    svg = _BG_RECT.sub("", svg, count=1)
    return svg.strip()


# ── 4. cache + top-level entry point ────────────────────────────────────────
def build_sketch(facts: dict, out_svg: Path, *, exposure: str = "internal",
                 detail: str = "overview", model: str = MODEL,
                 force: bool = False) -> dict:
    """The whole pipeline: spec -> cache check -> draw call -> sanitise -> write.
    Returns {"svg", "spec", "hash", "cached", "summary"}. Never redraws when the
    structured input hasn't changed (spec §16b: "otherwise every cadence run
    burns a call and churns the image") unless `force`."""
    spec = build_diagram_spec(facts, exposure=exposure, detail=detail)
    ihash = _input_hash(spec)
    hash_path = out_svg.with_suffix(".inputhash")

    if not force and out_svg.is_file() and hash_path.is_file() \
            and hash_path.read_text().strip() == ihash:
        return {"svg": out_svg.read_text(), "spec": spec, "hash": ihash,
               "cached": True, "summary": None}

    payload = call_draw_agent(spec, model=model)
    svg = sanitise_svg(payload["svg"])
    if "<svg" not in svg[:20]:
        raise DrawError(f"sanitised output has no <svg> root: {svg[:120]!r}")

    out_svg.parent.mkdir(parents=True, exist_ok=True)
    out_svg.write_text(svg)
    hash_path.write_text(ihash)
    return {"svg": svg, "spec": spec, "hash": ihash, "cached": False,
           "summary": payload.get("summary")}
