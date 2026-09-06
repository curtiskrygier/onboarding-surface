import argparse
import json
from pathlib import Path

from review.review import build


def main() -> int:
    ap = argparse.ArgumentParser(prog="review")
    ap.add_argument("--facts", required=True)
    ap.add_argument("--docs", required=True, help="dir holding the rendered README/ARCHITECTURE/CONTRIBUTING")
    ap.add_argument("--repo", required=True, help="the onboarded repo (for the diff vs current + the sketch)")
    ap.add_argument("--out", default="review.html")
    a = ap.parse_args()

    facts = json.load(open(a.facts))
    html_doc = build(facts, Path(a.docs), Path(a.repo))
    Path(a.out).write_text(html_doc)
    print(f"wrote {a.out}  ({len(html_doc)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
