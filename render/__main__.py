import argparse
import json
from pathlib import Path

from render.render import render


def main() -> int:
    ap = argparse.ArgumentParser(prog="render")
    ap.add_argument("facts")
    ap.add_argument("--authored")
    ap.add_argument("--exposure", choices=["internal", "public"], default="internal")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--fresh", action="store_true",
                    help="ignore existing target files; emit only the generated blocks")
    a = ap.parse_args()

    facts = json.load(open(a.facts))
    authored = json.load(open(a.authored)) if a.authored else {}
    res = render(facts, authored, exposure=a.exposure, fresh=a.fresh)

    od = Path(a.out_dir)
    od.mkdir(parents=True, exist_ok=True)
    # MAINTAINER-NOTES.md is a public-mode artefact only — clear a stale one so
    # an internal re-render of the same dir doesn't leave it behind.
    if "MAINTAINER-NOTES.md" not in res:
        (od / "MAINTAINER-NOTES.md").unlink(missing_ok=True)
    for name, text in res.items():
        (od / name).write_text(text)
        print(f"wrote {od/name}  ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
