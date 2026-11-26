#!/usr/bin/env python3
"""Gate: run metrics.py checks on every Przed/Po example inside a SKILL.md.

Usage:
    gate_examples.py SKILL.md [--ref reference/smigiel.json] [--json]

Exit 1 when any example's "Po" contains fabrication candidates (numbers,
proper nouns, quotes, URLs absent from "Przed") or introduces a GPT-ism from
the skill's own §30/§31 lists. Examples teach the model; an example that
violates the skill's rules is a bug in the skill.

Pairs recognised:
  - inline:  **Przed:** ...  /  **Po:** ...        (one paragraph each)
  - block:   ### Przed ...: / ### Po ...:          (until next heading)
  - full:    ### Tekst wejściowy ...  ->  ### Druga redakcja: (or Finalna wersja with text)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics  # noqa: E402

INLINE_RE = re.compile(r"^\*\*Przed:\*\*\s*(.+?)\n\n\*\*Po:\*\*\s*(.+?)(?=\n\n|\Z)", re.MULTILINE | re.DOTALL)
BLOCK_RE = re.compile(r"^### Przed[^\n]*\n(.*?)\n### Po[^\n]*\n(.*?)(?=\n### |\n## |\Z)", re.MULTILINE | re.DOTALL)
FULL_IN_RE = re.compile(r"^### Tekst wejściowy[^\n]*\n(.*?)(?=\n### )", re.MULTILINE | re.DOTALL)
FULL_OUT_RE = re.compile(r"^### Druga redakcja:?\n(.*?)(?=\n### )", re.MULTILINE | re.DOTALL)


def section_of(text: str, pos: int) -> str:
    heads = [(m.start(), m.group(1)) for m in re.finditer(r"^###? (.+)$", text, re.MULTILINE)]
    label = "?"
    for start, name in heads:
        if start <= pos:
            label = name
    return label.strip()[:60]


def collect_pairs(text: str) -> list[tuple[str, str, str]]:
    pairs: list[tuple[str, str, str]] = []
    for m in INLINE_RE.finditer(text):
        pairs.append((section_of(text, m.start()), m.group(1), m.group(2)))
    for m in BLOCK_RE.finditer(text):
        pairs.append((section_of(text, m.start()), m.group(1), m.group(2)))
    fi, fo = FULL_IN_RE.search(text), FULL_OUT_RE.search(text)
    if fi and fo:
        pairs.append(("Pełny przykład (wejście -> Druga redakcja)", fi.group(1), fo.group(1)))
    return pairs


def clean(s: str) -> str:
    s = metrics.strip_markdown_quote(s)
    s = re.sub(r"\*\*|\*|`", "", s)  # markdown emphasis
    return s.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skill", type=Path)
    ap.add_argument("--ref", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    text = args.skill.read_text(encoding="utf-8")
    metrics.GPTISMS[:] = metrics.load_skill_phrases(args.skill)
    ref = json.loads(args.ref.read_text(encoding="utf-8")) if args.ref else None
    ktory_p95 = ref["human"]["ktory_per100"]["p95"] if ref else None

    results = []
    for section, before, after in collect_pairs(text):
        before, after = clean(before), clean(after)
        d = metrics.diff_report(before, after)
        fab = {k: v for k, v in d["fabrication_candidates"].items() if v}
        ma = metrics.analyze(after)
        issues: list[str] = []
        warnings: list[str] = []
        if fab:
            issues.append(f"fabrication: {fab}")
        if d["introduced_gptisms"]:
            issues.append(f"introduced_gptisms: {d['introduced_gptisms']}")
        pd, pa = d["punct_delta_per100"], d["punct_delta_abs"]
        if ma.words >= 40 and pd["dashes"] < 0 and pd["commas"] > 1.0:
            issues.append(f"dash->comma: Δdashes {pd['dashes']:+.2f}/100, Δcommas {pd['commas']:+.2f}/100")
        elif ma.words < 40 and pa["dashes"] <= -2 and pa["commas"] >= 1:
            issues.append(f"dash->comma (abs): {pa['dashes']:+d} myślników, {pa['commas']:+d} przecinków")
        if d["dropped_qualifiers"]:
            issues.append(f"dropped_qualifiers: {d['dropped_qualifiers']}")
        if d["novel_content_share"] >= 0.6:
            warnings.append(f"novel_content {d['novel_content_share']:.0%} (możliwe nowe twierdzenia - przeczytaj)")
        if ktory_p95 is not None and ma.words >= 40 and ma.ktory_per100 > ktory_p95:
            issues.append(f"ktory_per100 {ma.ktory_per100} > human p95 {ktory_p95}")
        results.append({"section": section, "words_after": ma.words, "issues": issues, "warnings": warnings})

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    else:
        for r in results:
            mark = "FAIL" if r["issues"] else ("warn" if r["warnings"] else "ok  ")
            print(f"{mark} [{r['section']}] ({r['words_after']} słów)")
            for i in r["issues"]:
                print(f"       - {i}")
            for w in r["warnings"]:
                print(f"       ~ WARN {w}")
        failed = sum(1 for r in results if r["issues"])
        print(f"\n{len(results)} par, {failed} FAIL")
    return 1 if any(r["issues"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
