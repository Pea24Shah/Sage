"""Score the checker on labelled claims:  python eval/run_eval.py eval/dev.json"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from citecheck import check_answer  # noqa: E402


def evaluate(path, supported_at=0.75, partly_at=0.5, verbose=True):
    data = json.loads(Path(path).read_text())
    ok = false_accept = false_flag = 0
    misses = []
    for c in data["claims"]:
        r = check_answer(c["text"], data["sources"], supported_at, partly_at)[0]
        said_supported = r.label == "Supported"
        gold = c["label"] == "supported"
        if said_supported == gold:
            ok += 1
        elif said_supported:
            false_accept += 1
            misses.append(("WRONGLY PASSED", c["text"], r))
        else:
            false_flag += 1
            misses.append(("WRONGLY FLAGGED", c["text"], r))
    n = len(data["claims"])
    if verbose:
        print(f"{Path(path).name}: {ok}/{n} correct ({ok / n:.0%}); "
              f"unsupported claims wrongly passed: {false_accept}; "
              f"supported claims wrongly flagged: {false_flag}")
        for kind, text, r in misses:
            print(f"  {kind}: {text}\n     -> {r.label} ({r.coverage})  {'; '.join(r.reasons)}")
    return ok, n, false_accept, false_flag


if __name__ == "__main__":
    evaluate(sys.argv[1])
