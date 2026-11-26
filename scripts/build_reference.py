#!/usr/bin/env python3
"""Build reference percentiles for metrics.py from PolEval 2025 Śmigiel.

Usage:
    build_reference.py path/to/2025-smigiel/data/train [--min-words 100] [-o reference/smigiel.json]

Human texts (label 0) give the reference distribution used by `metrics.py --ref`.
AI texts (label 1, open-weights models 2024-25 continuing a human prefix) are
stored alongside for context only; they are NOT a model of Claude/GPT output.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import analyze  # noqa: E402

FIELDS = [
    "em_dash_per100", "en_dash_per100", "ktory_per100", "commas_per100", "parens_per100",
    "punct_other_share", "punct_entropy", "sent_len_mean", "sent_len_cv", "ttr", "gptisms_per100",
]
PCTS = [5, 25, 50, 75, 95]


def percentiles(values: list[float]) -> dict[str, float]:
    if len(values) < 20:
        return {}
    qs = statistics.quantiles(values, n=100, method="inclusive")
    return {f"p{p}": round(qs[p - 1], 3) for p in PCTS}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("train_dir", type=Path)
    ap.add_argument("--min-words", type=int, default=100)
    ap.add_argument("-o", "--out", type=Path, default=Path(__file__).parent.parent / "reference" / "smigiel.json")
    args = ap.parse_args()

    # str.splitlines() also splits on U+2028/U+0085 inside texts; use plain newline.
    texts = (args.train_dir / "data.tsv").read_text(encoding="utf-8").rstrip("\n").split("\n")
    labels = (args.train_dir / "labels.tsv").read_text(encoding="utf-8").split()
    assert len(texts) == len(labels), (len(texts), len(labels))

    buckets: dict[str, dict[str, list[float]]] = {"human": {f: [] for f in FIELDS}, "ai": {f: [] for f in FIELDS}}
    n = {"human": 0, "ai": 0}
    for text, label in zip(texts, labels):
        m = analyze(text)
        if m.words < args.min_words:
            continue
        key = "human" if label == "0" else "ai"
        n[key] += 1
        for f in FIELDS:
            buckets[key][f].append(getattr(m, f))

    out = {
        "source": "PolEval 2025 Task 1 Śmigiel, data/train (github.com/poleval/2025-smigiel)",
        "min_words": args.min_words,
        "n": n,
        "note": "AI texts = open-weights models (Bielik, PLLuM, Llama, Mistral, Gemma) continuing a human prefix. "
                "Use 'human' as the reference; 'ai' is context, not a model of Claude/GPT output.",
        "human": {f: percentiles(v) for f, v in buckets["human"].items()},
        "ai": {f: percentiles(v) for f, v in buckets["ai"].items()},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {args.out}  n={n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
