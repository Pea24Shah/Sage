"""Command line:  python -m citecheck answer.txt source1.txt [source2.txt ...]"""
import argparse
import sys
from pathlib import Path

from .core import check_answer, summarize

MARK = {"Supported": "[OK]  ", "Partly supported": "[?]   ",
        "Possible contradiction": "[!]   ", "Unsupported": "[X]   "}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="citecheck", description=__doc__)
    ap.add_argument("answer", help="text file containing the AI answer")
    ap.add_argument("sources", nargs="+", help="one or more source text files")
    ap.add_argument("--supported-at", type=float, default=0.75)
    ap.add_argument("--partly-at", type=float, default=0.5)
    a = ap.parse_args(argv)

    answer = Path(a.answer).read_text(encoding="utf-8")
    sources = {Path(s).name: Path(s).read_text(encoding="utf-8")
               for s in a.sources}
    results = check_answer(answer, sources, a.supported_at, a.partly_at)
    for r in results:
        print(f"{MARK[r.label]}{r.label} ({r.coverage:.2f})  {r.claim}")
        if r.label != "Unsupported" or r.coverage >= 0.3:
            print(f"        best match [{r.source}]: {r.passage}")
        for why in r.reasons:
            print(f"        note: {why}")
        print()
    s = summarize(results)
    print("Summary: " + ", ".join(f"{v} {k.lower()}" for k, v in s.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
