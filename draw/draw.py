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


# facts.structure.modules is ranked by real file count, which favours large
# generic scaffolding (tests/, scripts/) over small but architecturally
# central surfaces (mcp/, googlechat/) when the box budget is tight —
# verified on a2ui-catalogue: raw ranking put tests/scripts/knowledge-catalogue
# ahead of mcp/renderers/cloud-run-renderer, so the diagram read as
# "apps-script-heavy, no web, no MCP" despite those surfaces being real and
# sized similarly to what DID make the cut. This doesn't drop anything or
# invent a "surface" label — it only reorders within the same real list so
# common infra/test/doc scaffolding yields its box-budget slot to product
# code when both are competing for the last few slots.
_LOW_PRIORITY_MODULE = re.compile(
    r"^(tests?|test-.*|.*-tests?|scripts?|examples?|docs?|spec|vendors?|"
    r"sampledocs|benchmarks?|payloads?|prompts?|runbooks?|articles?|skills|"
    r"knowledge-catalogue)$", re.I)


def _rank_modules(modules: list[str]) -> list[str]:
    primary = [m for m in modules if not _LOW_PRIORITY_MODULE.match(m)]
    secondary = [m for m in modules if _LOW_PRIORITY_MODULE.match(m)]
    return primary + secondary


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

    for m in _rank_modules(s["modules"])[:mod_budget]:
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


# ── 2. box/edge/zone spec -> D2 source -> `d2` CLI ──────────────────────────
# Superseded 2026-09-06: a freeform_canvas LLM call drew the sketch freehand
# (guessing box positions itself). Curtis, on seeing the result next to the
# original hand-tuned test: "did not look as professional... revisit the
# prompt, including graphic size." D2 (github.com/terrastruct/d2, a real
# diagram-layout engine, already installed) does the layout properly and
# deterministically from the exact same box/edge/zone spec — no prompt to
# tune, no canvas-size guessing, no chance of an invented relationship. This
# also means §16b no longer calls an LLM at all: it's as deterministic as
# `render` itself. §16c (the mark) still needs a real generative call — D2
# lays out known structure, it doesn't invent a metaphor — so the
# freeform_canvas path stays for that job, further down.

D2_THEME = 0   # "Neutral Default" — Curtis's pick 2026-09-06 over Cool
              # Classics / sketch (hand-drawn) mode, compared side by side.


class DrawError(RuntimeError):
    pass


class D2Error(DrawError):
    pass


def _d2_str(s: str) -> str:
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_d2_source(spec: dict) -> str:
    """Deterministic translation of build_diagram_spec()'s output into D2
    source. No layout decisions made here — `d2` does those; this only maps
    real facts (already in `spec`) onto D2 syntax."""
    boxes_by_id = {b["id"]: b for b in spec["boxes"]}
    by_zone: dict[str, list[dict]] = {}
    for b in spec["boxes"]:
        by_zone.setdefault(b["zone"], []).append(b)
    edges_by_zone: dict[str, list[dict]] = {}
    for e in spec["edges"]:
        zone = (boxes_by_id.get(e["from"]) or boxes_by_id.get(e["to"]) or {}).get("zone")
        edges_by_zone.setdefault(zone, []).append(e)

    lines = []
    for zone in spec["zones"]:
        lines.append(f"{_d2_str(zone['id'])}: {_d2_str(zone['title'])} {{")
        lines.append(f"  direction: {'down' if zone['direction'] == 'top-down' else 'right'}")
        for b in by_zone.get(zone["id"], []):
            bid, blabel = _d2_str(b["id"]), _d2_str(b["label"])
            if b.get("accent"):
                lines.append(f"  {bid}: {blabel} {{")
                lines.append(f'    style.fill: "{_ENTRY_ACCENT}"')
                lines.append('    style.font-color: "#ffffff"')
                lines.append("    style.bold: true")
                lines.append("  }")
            else:
                lines.append(f"  {bid}: {blabel}")
        for e in edges_by_zone.get(zone["id"], []):
            fid, tid = _d2_str(e["from"]), _d2_str(e["to"])
            tail = f": {_d2_str(e['label'])}" if e.get("label") else ""
            lines.append(f"  {fid} -> {tid}{tail}")
        lines.append("}")
    return "\n".join(lines)


def render_d2(d2_source: str, out_svg: Path, *, theme: int = D2_THEME,
             pad: int = 40, sketch: bool = False, timeout: int = 30) -> None:
    """Shells out to the real `d2` CLI — a real layout engine, not a model
    guessing coordinates. Deterministic given the same source + flags."""
    import subprocess
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".d2", delete=False) as tf:
        tf.write(d2_source)
        d2_path = Path(tf.name)
    try:
        cmd = ["d2", "--theme", str(theme), "--pad", str(pad)]
        if sketch:
            cmd.append("--sketch")
        cmd += [str(d2_path), str(out_svg)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except FileNotFoundError as e:
            raise D2Error("the `d2` CLI is not on PATH — see "
                          "https://d2lang.com/tour/install") from e
        except subprocess.TimeoutExpired as e:
            raise D2Error(f"d2 did not finish within {timeout}s") from e
        if r.returncode != 0:
            raise D2Error(f"d2 compile failed: {r.stderr.strip()[:500]}")
    finally:
        d2_path.unlink(missing_ok=True)


# ── 3. deterministic SVG post-processing (never trust raw model output) ────
_FORBIDDEN_TAGS = re.compile(
    r"<\s*(script|foreignObject|iframe|object|embed|image)\b.*?(?:/>|</\s*\1\s*>)",
    re.I | re.S)
_EVENT_ATTR = re.compile(r'\s+on\w+\s*=\s*"[^"]*"', re.I)
_STYLE_TAG = re.compile(r"<\s*style\b.*?</\s*style\s*>", re.I | re.S)
_BAD_URL_ATTR = re.compile(
    r'\s+(href|xlink:href)\s*=\s*"(?!#)[^"]*"', re.I)
_NUM = r"-?\d+(?:\.\d+)?"


def _attr(tag: str, name: str) -> float | None:
    m = re.search(rf'\b{name}\s*=\s*"({_NUM})"', tag)
    return float(m.group(1)) if m else None


def _viewbox_dims(svg: str) -> tuple[float, float] | None:
    m = re.search(rf'viewBox\s*=\s*"[^"]*?\s+({_NUM})\s+({_NUM})\s*"', svg)
    return (float(m.group(1)), float(m.group(2))) if m else None


def _strip_full_canvas_bg_rect(svg: str) -> str:
    """A full-canvas background rect the model drew anyway despite being told
    not to — sized to the viewBox (or `100%`), not a hardcoded viewBox like
    16b's fixed 1100x700. Shared between the sketch (16b) and the mark (16c)
    since both forbid a baked background."""
    dims = _viewbox_dims(svg)
    for m in re.finditer(r"<rect\b[^>]*/?>", svg):
        tag = m.group(0)
        x, y = _attr(tag, "x") or 0, _attr(tag, "y") or 0
        if x or y:
            continue
        if 'width="100%"' in tag or 'height="100%"' in tag:
            return svg[:m.start()] + svg[m.end():]
        w, h = _attr(tag, "width"), _attr(tag, "height")
        if dims and w is not None and h is not None \
                and abs(w - dims[0]) < 1 and abs(h - dims[1]) < 1:
            return svg[:m.start()] + svg[m.end():]
    return svg


def sanitise_svg(svg: str) -> str:
    """Strip anything dangerous in an embedded static asset, and the baked
    full-canvas background the prompt already forbids. Never rewrites content,
    only removes — same "flag, don't mangle" discipline as render's leak scan."""
    svg = _FORBIDDEN_TAGS.sub("", svg)
    svg = _STYLE_TAG.sub("", svg)
    svg = _EVENT_ATTR.sub("", svg)
    svg = _BAD_URL_ATTR.sub("", svg)
    svg = _strip_full_canvas_bg_rect(svg)
    return svg.strip()


# ── 4. cache + top-level entry point ────────────────────────────────────────
def build_sketch(facts: dict, out_svg: Path, *, exposure: str = "internal",
                 detail: str = "overview", theme: int = D2_THEME,
                 force: bool = False) -> dict:
    """The whole pipeline: spec -> cache check -> D2 source -> `d2` -> write.
    Returns {"svg", "spec", "hash", "cached"}. Never redraws when the
    structured input hasn't changed (spec §16b: "otherwise every cadence run
    churns the image") unless `force` — cheap to keep even though `d2` itself
    is fast and free of API cost, since it still means a real file write and a
    changed embed on every render otherwise."""
    spec = build_diagram_spec(facts, exposure=exposure, detail=detail)
    ihash = _input_hash(spec)
    hash_path = out_svg.with_suffix(".inputhash")

    if not force and out_svg.is_file() and hash_path.is_file() \
            and hash_path.read_text().strip() == ihash:
        return {"svg": out_svg.read_text(), "spec": spec, "hash": ihash, "cached": True}

    out_svg.parent.mkdir(parents=True, exist_ok=True)
    render_d2(build_d2_source(spec), out_svg, theme=theme)
    hash_path.write_text(ihash)
    return {"svg": out_svg.read_text(), "spec": spec, "hash": ihash, "cached": False}


# ── 5. §16c: repo mark — invents a metaphor, so a human must pick ──────────
# Unlike 16b (known boxes, layout only), a mark is the model's own concept —
# the shakiest thing a one-shot generator does (tested 2026-09-06 for
# onboarding-surface itself: two concepts, one read as "a chromosome", one
# landed). So this path only ever PROPOSES; nothing here writes into a repo's
# assets/ except adopt_mark(), and that's a separate, explicit, human-invoked
# step — never called by propose_marks() or by onboard.py's own pipeline.

_MARK_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "candidates": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "concept": {"type": "STRING"},
                    "justification": {"type": "STRING"},
                    "svg": {"type": "STRING"},
                },
                "required": ["concept", "justification", "svg"],
            },
        },
    },
    "required": ["candidates"],
}

_MARK_SYSTEM = """You design a minimal geometric mark (an abstract logo) as raw
SVG markup, using the freeform_canvas atom's rules.

Rules, per candidate:
- Root element `<svg>`; viewBox="0 0 240 240"; transparent background — no
  full-canvas background rect; no width/height attrs on the root.
- At most 5 shapes total. NO TEXT anywhere — a wordmark is a separate concern.
- Flat fills only — no gradients, no shadows, no photographic detail.
- One accent colour (choose a real hex value fitting the concept) plus
  neutral/transparent — not a rainbow.
- Centred in the viewBox with a generous margin — must read clearly at 24x24px.
- No <script>, <foreignObject>, <image>, <iframe>, <object>, <embed>, no
  event-handler attributes, no external URLs, no <style> element.

Generate exactly the number of candidates requested, each a GENUINELY DISTINCT
visual metaphor for the concept seed below — not colour or minor-shape
variations of one idea. For each: a short concept name (2-4 words), a
one-sentence justification tying it to the seed, and the svg markup.

Return ONLY the JSON object: candidates (array, each {concept, justification, svg})."""

_MARK_HINT = re.compile(r"logo|banner|wordmark|brand|favicon", re.I)


def build_mark_seed(facts: dict) -> dict:
    """The ONLY input to the mark prompt — real facts.repo fields, nothing
    invented here either."""
    repo = facts["repo"]
    return {"name": repo.get("name"), "description": repo.get("description"),
           "topics": repo.get("topics"), "repo_kind": facts.get("repo_kind")}


def has_existing_mark(repo: Path) -> bool:
    """Spec §16c's own guard: only propose a mark where none exists."""
    if any(repo.glob("assets/logo*")) or any(repo.glob("assets/favicon*")):
        return True
    gh = repo / ".github"
    if gh.is_dir() and any(_MARK_HINT.search(p.name) for p in gh.iterdir()):
        return True
    readme = repo / "README.md"
    if readme.is_file():
        head = readme.read_text(errors="replace")[:2000]
        if re.search(r'<img[^>]+src="[^"]*"', head) and _MARK_HINT.search(head[:2000]):
            return True
    return False


def call_mark_agent(seed: dict, *, n: int = 3, model: str = MODEL,
                    timeout: int = 90) -> list[dict]:
    prompt = (f"CONCEPT SEED:\n{json.dumps(seed, indent=1)}\n\n"
             f"Generate {n} distinct candidate concepts.")
    try:
        resp = vx.call(model, [{"role": "user", "parts": [{"text": prompt}]}],
                       system=_MARK_SYSTEM, schema=_MARK_SCHEMA,
                       # higher temperature than the sketch call (0.4) — here
                       # DIVERSITY across concepts is the point, not fidelity
                       # to a fixed input.
                       # N full svg+justification candidates in one call needs
                       # real headroom -- 8000 truncated mid-string on a live
                       # 3-candidate call, 2026-09-06 (same failure mode noted
                       # in streaming-testbench's own freeform_demo.py).
                       temperature=0.9, max_output_tokens=20000, timeout=timeout)
        part = vx.first_part(resp)
    except Exception as e:  # noqa: BLE001
        raise DrawError(f"draw agent (mark) call failed: {e}") from e
    text = (part or {}).get("text")
    if not text:
        raise DrawError("draw agent returned no text content")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        raise DrawError(f"draw agent reply was not JSON ({e}): {text[:200]}") from e
    cands = parsed.get("candidates") or []
    if not cands:
        raise DrawError("draw agent returned zero candidates")
    return cands


def _svg_bbox(svg: str) -> tuple[float, float, float, float] | None:
    """Approximate bounding box of every drawn shape, attribute-aware (not a
    blind number scan — that would pick up stroke-width etc). Good enough for
    a flat, few-shape mark; path curves are approximated by their control/end
    points, which is fine for the flat/minimal shapes the prompt asks for."""
    pts: list[tuple[float, float]] = []
    for m in re.finditer(r"<rect\b[^>]*/?>", svg):
        t = m.group(0)
        x, y, w, h = _attr(t, "x") or 0, _attr(t, "y") or 0, _attr(t, "width"), _attr(t, "height")
        if w is not None and h is not None:
            pts += [(x, y), (x + w, y + h)]
    for m in re.finditer(r"<circle\b[^>]*/?>", svg):
        t = m.group(0)
        cx, cy, r = _attr(t, "cx") or 0, _attr(t, "cy") or 0, _attr(t, "r")
        if r is not None:
            pts += [(cx - r, cy - r), (cx + r, cy + r)]
    for m in re.finditer(r"<ellipse\b[^>]*/?>", svg):
        t = m.group(0)
        cx, cy = _attr(t, "cx") or 0, _attr(t, "cy") or 0
        rx, ry = _attr(t, "rx"), _attr(t, "ry")
        if rx is not None and ry is not None:
            pts += [(cx - rx, cy - ry), (cx + rx, cy + ry)]
    for m in re.finditer(r"<line\b[^>]*/?>", svg):
        t = m.group(0)
        x1, y1, x2, y2 = _attr(t, "x1"), _attr(t, "y1"), _attr(t, "x2"), _attr(t, "y2")
        if None not in (x1, y1, x2, y2):
            pts += [(x1, y1), (x2, y2)]
    for m in re.finditer(r'<poly(?:line|gon)\b[^>]*\bpoints\s*=\s*"([^"]+)"', svg):
        nums = [float(n) for n in re.findall(_NUM, m.group(1))]
        pts += list(zip(nums[0::2], nums[1::2]))
    for m in re.finditer(r'<path\b[^>]*\bd\s*=\s*"([^"]+)"', svg):
        nums = [float(n) for n in re.findall(_NUM, m.group(1))]
        pts += list(zip(nums[0::2], nums[1::2]))
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def tighten_viewbox(svg: str, pad: float = 24) -> str:
    """§16c post-processing step 2: tighten viewBox to the artwork bounding
    box + even padding. 16b keeps its generous FIXED canvas instead — this
    only applies to the mark, where the whole point is a tight, centred glyph."""
    bbox = _svg_bbox(svg)
    if not bbox:
        return svg
    minx, miny, maxx, maxy = bbox
    minx, miny = minx - pad, miny - pad
    w, h = (maxx - minx) + pad, (maxy - miny) + pad
    return re.sub(r'viewBox\s*=\s*"[^"]*"', f'viewBox="{minx:g} {miny:g} {w:g} {h:g}"',
                 svg, count=1)


def _drop_redundant_attrs(svg: str) -> str:
    """§16c post-processing step 3: `ry` alongside an equal `rx`, and
    `width`/`height` on the root `<svg>` once `viewBox` is set."""
    def _rect_fix(m: re.Match) -> str:
        t = m.group(0)
        rx, ry = _attr(t, "rx"), _attr(t, "ry")
        if rx is not None and ry is not None and rx == ry:
            t = re.sub(r'\s+ry\s*=\s*"[^"]*"', "", t)
        return t
    svg = re.sub(r"<rect\b[^>]*/?>", _rect_fix, svg)
    root_attr = re.compile(r'(<svg\b[^>]*?)\s+(?:width|height)\s*=\s*"[^"]*"')
    svg = root_attr.sub(r"\1", svg)
    svg = root_attr.sub(r"\1", svg)  # a second pass catches whichever attr came second
    return svg


_COLOR_ATTR = re.compile(r'\b(fill|stroke)\s*=\s*"(#[0-9a-fA-F]{3,8}|[a-zA-Z]+)"')


def to_monochrome(svg: str) -> str:
    """§16c post-processing step 4: a `currentColor` variant alongside the
    coloured one, so the mark can sit on a dark surface or a single-colour
    favicon context. `none`/`transparent` are left alone — they're not a colour
    to swap."""
    def _sub(m: re.Match) -> str:
        attr, val = m.group(1), m.group(2)
        if val.lower() in ("none", "transparent"):
            return m.group(0)
        return f'{attr}="currentColor"'
    return _COLOR_ATTR.sub(_sub, svg)


def postprocess_mark(svg: str) -> str:
    svg = sanitise_svg(svg)
    svg = tighten_viewbox(svg)
    svg = _drop_redundant_attrs(svg)
    return svg


def propose_marks(facts: dict, out_dir: Path, *, n: int = 3, model: str = MODEL,
                  timeout: int = 90) -> list[dict]:
    """§16c: generates `n` candidate marks in ONE call, post-processes each,
    writes them to `out_dir` for a human to review. NEVER adopted here —
    returns the manifest [{concept, justification, file, mono_file}] that also
    gets written as `out_dir/manifest.json`."""
    seed = build_mark_seed(facts)
    cands = call_mark_agent(seed, n=n, model=model, timeout=timeout)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for i, c in enumerate(cands, 1):
        svg = postprocess_mark(c.get("svg", ""))
        if "<svg" not in svg[:20]:
            continue  # one bad candidate doesn't fail the whole batch
        mono = to_monochrome(svg)
        f, fm = out_dir / f"mark-{i}.svg", out_dir / f"mark-{i}-mono.svg"
        f.write_text(svg)
        fm.write_text(mono)
        manifest.append({"concept": c.get("concept", f"concept {i}"),
                        "justification": c.get("justification", ""),
                        "file": str(f), "mono_file": str(fm)})
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


def adopt_mark(picked_svg: Path, repo: Path) -> dict:
    """The ONLY function in this module that writes into an actual repo's
    assets/ — always a separate, explicit, human-invoked step, never called by
    propose_marks() or by onboard.py's own pipeline."""
    assets = repo / "assets"
    assets.mkdir(exist_ok=True)
    svg = picked_svg.read_text()
    (assets / "logo.svg").write_text(svg)
    (assets / "favicon.svg").write_text(svg)
    result = {"logo": assets / "logo.svg", "favicon": assets / "favicon.svg", "mono": None}
    mono_candidate = picked_svg.with_name(picked_svg.stem + "-mono.svg")
    if mono_candidate.is_file():
        (assets / "logo-mono.svg").write_text(mono_candidate.read_text())
        result["mono"] = assets / "logo-mono.svg"
    return result
