import argparse
import json
import sys
from pathlib import Path

from draw.draw import DrawError, build_sketch


def main() -> int:
    ap = argparse.ArgumentParser(prog="draw")
    ap.add_argument("facts")
    ap.add_argument("--out", help="target .svg path (default: "
                                  "<repo>/assets/onboarding/architecture-sketch.svg)")
    ap.add_argument("--exposure", choices=["internal", "public"], default="internal")
    ap.add_argument("--detail", choices=["overview", "detailed"], default="overview")
    ap.add_argument("--model", default="gemini-3.8-flash")
    ap.add_argument("--force", action="store_true", help="ignore the input-hash cache")
    a = ap.parse_args()

    facts = json.load(open(a.facts))
    out_svg = Path(a.out) if a.out else \
        Path(facts["_repo_path"]) / "assets/onboarding/architecture-sketch.svg"

    try:
        result = build_sketch(facts, out_svg, exposure=a.exposure, detail=a.detail,
                              model=a.model, force=a.force)
    except DrawError as e:
        sys.exit(f"draw: {e}")

    if result["cached"]:
        print(f"unchanged (hash {result['hash']}) — kept {out_svg}", file=sys.stderr)
    else:
        print(f"wrote {out_svg}  ({len(result['svg'])} bytes)", file=sys.stderr)
        if result.get("summary"):
            print(f"  summary: {result['summary']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
