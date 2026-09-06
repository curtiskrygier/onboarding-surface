import argparse
import json
import sys
from pathlib import Path

from draw.draw import (DrawError, adopt_mark, build_sketch, has_existing_mark,
                       propose_marks)


def main() -> int:
    ap = argparse.ArgumentParser(prog="draw")
    sub = ap.add_subparsers(dest="job", required=True)

    p1 = sub.add_parser("architecture", help="spec §16b — the architecture sketch (D2, deterministic)")
    p1.add_argument("facts")
    p1.add_argument("--out", help="target .svg path (default: "
                                  "<repo>/assets/onboarding/architecture-sketch.svg)")
    p1.add_argument("--exposure", choices=["internal", "public"], default="internal")
    p1.add_argument("--detail", choices=["overview", "detailed"], default="overview")
    p1.add_argument("--force", action="store_true", help="ignore the input-hash cache")

    p2 = sub.add_parser("mark", help="spec §16c — propose N repo-mark candidates (never auto-adopted)")
    p2.add_argument("facts")
    p2.add_argument("--out-dir", help="default: <repo>/assets/onboarding/mark-candidates")
    p2.add_argument("--n", type=int, default=3)
    p2.add_argument("--model", default="gemini-3.8-flash")
    p2.add_argument("--force", action="store_true",
                    help="propose even if the repo already has a mark")

    p3 = sub.add_parser("adopt-mark", help="copy one picked candidate into <repo>/assets/")
    p3.add_argument("pick", help="path to the chosen mark-N.svg")
    p3.add_argument("--repo", required=True)

    a = ap.parse_args()

    if a.job == "architecture":
        facts = json.load(open(a.facts))
        out_svg = Path(a.out) if a.out else \
            Path(facts["_repo_path"]) / "assets/onboarding/architecture-sketch.svg"
        try:
            result = build_sketch(facts, out_svg, exposure=a.exposure, detail=a.detail,
                                  force=a.force)
        except DrawError as e:
            sys.exit(f"draw: {e}")
        if result["cached"]:
            print(f"unchanged (hash {result['hash']}) — kept {out_svg}", file=sys.stderr)
        else:
            print(f"wrote {out_svg}  ({len(result['svg'])} bytes)", file=sys.stderr)
        return 0

    if a.job == "mark":
        facts = json.load(open(a.facts))
        repo = Path(facts["_repo_path"])
        if not a.force and has_existing_mark(repo):
            sys.exit("draw: repo already has a mark (assets/logo*, favicon.svg, or "
                     "a README image) — pass --force to propose anyway")
        out_dir = Path(a.out_dir) if a.out_dir else repo / "assets/onboarding/mark-candidates"
        try:
            manifest = propose_marks(facts, out_dir, n=a.n, model=a.model)
        except DrawError as e:
            sys.exit(f"draw: {e}")
        if not manifest:
            sys.exit("draw: no candidate survived post-processing — try again")
        print(f"wrote {len(manifest)} candidate(s) to {out_dir}:", file=sys.stderr)
        for m in manifest:
            print(f"  {m['file']}  — {m['concept']}: {m['justification']}", file=sys.stderr)
        print("Not adopted. Review, then:\n"
             f"  python3 -m draw adopt-mark <picked.svg> --repo {repo}", file=sys.stderr)
        return 0

    if a.job == "adopt-mark":
        result = adopt_mark(Path(a.pick), Path(a.repo))
        print(f"wrote {result['logo']}", file=sys.stderr)
        print(f"wrote {result['favicon']}", file=sys.stderr)
        if result["mono"]:
            print(f"wrote {result['mono']}", file=sys.stderr)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
