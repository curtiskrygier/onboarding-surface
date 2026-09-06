"""python3 -m extract <repo-path> [--out FILE] [--github]"""
import argparse
import json
import sys

from extract.facts import build


def main() -> int:
    ap = argparse.ArgumentParser(prog="extract", description=__doc__)
    ap.add_argument("repo", help="path to a local git repo")
    ap.add_argument("--out", help="write facts.json here (default: stdout)")
    ap.add_argument("--github", action="store_true",
                    help="also mine starter issues + review comments (needs gh / a token)")
    ap.add_argument("--compact", action="store_true", help="one-line JSON")
    args = ap.parse_args()

    facts = build(args.repo, github=args.github)
    text = json.dumps(facts, separators=(",", ":")) if args.compact else json.dumps(facts, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text + "\n")
        print(f"wrote {args.out}  ({len(text)} bytes)", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
