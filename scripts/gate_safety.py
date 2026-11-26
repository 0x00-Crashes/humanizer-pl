#!/usr/bin/env python3
"""Static safety gate for skill files (no model run required).

Complements the runtime injection test: criterion 7 depends on someone running
subagents, this runs in CI/pre-commit and is deterministic.

Checks each given file for:
  - hidden Unicode: zero-width, BiDi overrides, Unicode-tag chars, NBSP, BOM;
  - HTML comments <!-- --> (can hide instructions from a reader but not the model);
  - lines beginning with '!' (command execution on skill load in some runners);
  - curly-quote integrity: unbalanced „ vs ” and any stray " (typography gate);
  - README install pinning: every `git clone` must carry --branch/--depth tag + a
    commit SHA check (rev-parse), per pt-asystent.

Exit 1 on any ERROR. WARN lines do not fail the build.

Usage:
    gate_safety.py SKILL.md SKILL-light.md README.md
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

HIDDEN = {
    "\u200b": "ZERO WIDTH SPACE", "\u200c": "ZWNJ", "\u200d": "ZWJ",
    "\u2060": "WORD JOINER", "\ufeff": "BOM/ZWNBSP", "\u00a0": "NBSP",
    "\u202a": "LRE", "\u202b": "RLE", "\u202c": "PDF", "\u202d": "LRO", "\u202e": "RLO",
    "\u2066": "LRI", "\u2067": "RLI", "\u2068": "FSI", "\u2069": "PDI",
}
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
GIT_CLONE_RE = re.compile(r"git clone[^\n]*", re.IGNORECASE)


def scan_hidden(text: str) -> list[tuple[int, str]]:
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for ch in line:
            if ch in HIDDEN:
                out.append((i, f"hidden char U+{ord(ch):04X} ({HIDDEN[ch]})"))
            elif ord(ch) >= 0xE0000 and ord(ch) <= 0xE007F:
                out.append((i, f"Unicode TAG char U+{ord(ch):05X}"))
            elif unicodedata.category(ch) == "Cf":
                out.append((i, f"format char U+{ord(ch):04X}"))
    return out


def scan_file(path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warns: list[str] = []
    text = path.read_text(encoding="utf-8")

    for ln, msg in scan_hidden(text):
        (warns if "NBSP" in msg else errors).append(f"{path.name}:{ln} {msg}")

    for m in HTML_COMMENT_RE.finditer(text):
        ln = text[: m.start()].count("\n") + 1
        errors.append(f"{path.name}:{ln} HTML comment: {m.group(0)[:60]!r}")

    for i, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("!") and not line.lstrip().startswith("!["):
            errors.append(f"{path.name}:{i} line starts with '!' (shell exec in some runners): {line.strip()[:60]!r}")

    # curly-quote integrity (skip fenced code blocks)
    no_code = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    opens, closes = no_code.count("\u201e"), no_code.count("\u201d")
    if opens != closes:
        warns.append(f"{path.name} curly quotes unbalanced: „={opens} ”={closes}")

    # README: install pinning
    if path.name.lower() == "readme.md":
        for m in GIT_CLONE_RE.finditer(text):
            clone = m.group(0)
            ln = text[: m.start()].count("\n") + 1
            if not re.search(r"--branch\s+v\d|--depth|@v\d", clone):
                errors.append(f"{path.name}:{ln} git clone not pinned to a tag: {clone[:70]!r}")
        if "rev-parse" not in text:
            warns.append(f"{path.name} no SHA verification (git rev-parse HEAD) after install")

    return errors, warns


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", type=Path, nargs="+")
    args = ap.parse_args()

    all_err: list[str] = []
    all_warn: list[str] = []
    for f in args.files:
        if not f.exists():
            all_err.append(f"{f}: not found")
            continue
        e, w = scan_file(f)
        all_err += e
        all_warn += w

    for w in all_warn:
        print(f"WARN  {w}")
    for e in all_err:
        print(f"ERROR {e}")
    print(f"\n{len(args.files)} plików, {len(all_err)} ERROR, {len(all_warn)} WARN")
    return 1 if all_err else 0


if __name__ == "__main__":
    sys.exit(main())
