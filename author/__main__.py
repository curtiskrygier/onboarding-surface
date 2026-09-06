import argparse
import json
import sys

from author.author import build_authored


def main() -> int:
    ap = argparse.ArgumentParser(prog="author")
    ap.add_argument("facts")
    ap.add_argument("--out", help="write authored.json here (default: stdout)")
    ap.add_argument("--model", default="gemini-3.8-flash")
    ap.add_argument("--exposure", choices=["internal", "public"], default="internal")
    a = ap.parse_args()

    facts = json.load(open(a.facts))
    authored = build_authored(facts, model=a.model, exposure=a.exposure)
    if authored.get("_warnings"):
        for w in authored["_warnings"]:
            print(f"  warn: {w}", file=sys.stderr)
    text = json.dumps(authored, indent=2)
    if a.out:
        with open(a.out, "w") as f:
            f.write(text + "\n")
        print(f"wrote {a.out}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
