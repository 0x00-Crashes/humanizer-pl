#!/usr/bin/env python3
"""Objective text metrics for humanizer-pl (Polish).

Replaces the self-assessed "Co jeszcze zdradza AI?" audit with numbers.
Pure standard library, Python 3.11+.

Usage:
    metrics.py TEXT                 # metrics for one text
    metrics.py BEFORE AFTER         # metrics for both + diff report
    metrics.py BEFORE AFTER --json  # machine-readable output

The diff report lists "fabrication candidates": numbers, proper nouns,
quoted phrases and URLs present in AFTER but absent from BEFORE. The skill's
own semantic audit only walks input -> output, so additions are invisible
to it by construction; this script walks the other direction.

Thresholds are NOT built in on purpose: densities depend on the author,
genre and model generation. Calibrate against a sample of the author's own
human-written text (see --baseline).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

WORD_RE = re.compile(r"[\w'\-]+", re.UNICODE)
SENT_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+(?=[A-ZĄĆĘŁŃÓŚŹŻ„\"(])")
NUMBER_RE = re.compile(r"\b\d+(?:[.,]\d+)?\s*%?")
URL_RE = re.compile(r"https?://\S+|\b[\w.-]+\.(?:pl|com|org|io|edu|gov)\b")
QUOTE_RE = re.compile(r"[„\"«»“”]([^„\"«»“”]{3,120})[”\"«»“]")
# Capitalised token not at sentence start: proper-noun candidate.
PROPER_RE = re.compile(r"(?<![.!?…]\s)(?<!^)\b([A-ZĄĆĘŁŃÓŚŹŻ][\w\-]{2,})", re.MULTILINE)

# Relative pronoun family: top discriminating feature for Polish LLM text
# in Kutyła et al. (PSiCL 2026). Counted per 100 words.
KTORY_RE = re.compile(
    r"\b(któr(?:y|a|e|ego|ej|emu|ym|ych|ymi|ą|zy))\b", re.IGNORECASE
)

# Fallback list, used only when no SKILL.md is available (see --skill / load_skill_phrases).
# Prefer the skill's own lists: a hand-made list produced false positives ("w ramach").
GPTISMS_FALLBACK = [
    "w dzisiejszym dynamicznym", "w dzisiejszych czasach", "warto zauważyć",
    "warto podkreślić", "należy podkreślić", "nie sposób nie", "kluczową rolę",
    "kluczowy", "istotn", "stanowi świadectwo", "w gruncie rzeczy",
    "podsumowując", "reasumując", "innymi słowy", "co więcej", "ponadto",
    "dodatkowo", "w kontekście", "w ramach", "na przestrzeni",
    "nie tylko", "lecz również", "zarówno", "jak i", "szeroki wachlarz",
    "przełomow", "transformacyjn", "pasjonując", "rysuje się", "podróż",
    "krajobraz", "ekosystem", "holistyczn", "synergi", "wyzwania i perspektywy",
]
GPTISMS: list[str] = list(GPTISMS_FALLBACK)


def load_skill_phrases(skill_md: Path) -> list[str]:
    """Extract the skill's own phrase lists: §30 calque table (first column)
    and §31 quoted GPT-isms. Trailing '...' / ', że' are stripped so the
    phrase matches mid-sentence. Returns lowercase phrases."""
    text = skill_md.read_text(encoding="utf-8")
    phrases: set[str] = set()
    sec30 = re.search(r"### 30\..*?(?=\n### 31\.)", text, re.DOTALL)
    if sec30:
        for row in re.findall(r"^\| ([^|*]+?) \| \*", sec30.group(0), re.MULTILINE):
            if not row.startswith("Kalka"):
                phrases.add(row.strip().lower())
    sec31 = re.search(r"### 31\..*?(?=\n### 32\.)", text, re.DOTALL)
    if sec31:
        for q in re.findall(r'"([^"]{4,60})"', sec31.group(0)):
            q = re.sub(r"\.\.\.$", "", q).strip()
            q = re.sub(r",?\s*(że|nad|do|się)$", "", q).strip()
            phrases.add(q.lower())
    # Single words are only kept when §31 lists them standalone (closers like
    # "Podsumowując", "Ponadto"); fragments such as "omówimy" are too generic.
    keep_single = {"ponadto"}
    return sorted(
        p for p in phrases
        if len(p) >= 4 and (" " in p or p.endswith("ując") or p in keep_single)
    )

# Spelled-out numerals (nominative/genitive stems) - count as "numbers" in fabrication check.
NUMERAL_RE = re.compile(
    r"\b(jedn\w*|dw[aóu]\w*|trz\w*|czter\w*|pięci\w*|pięć|sześ\w*|siedm\w*|siedem|ośmi\w*|osiem|"
    r"dziewię\w*|dziesię\w*|kilk\w*|kilkanaś\w*|kilkudziesię\w*|set\w*|tysiąc\w*|milion\w*|połow\w*|"
    r"pierwsz\w*|drugi\w*|trzeci\w*)\b", re.IGNORECASE)

# Quantifiers / hedges whose silent removal changes a claim (modality, scope).
QUALIFIERS = [
    "ponad", "około", "ok.", "co najmniej", "przynajmniej", "najwyżej", "prawie", "niemal", "blisko",
    "częściowo", "zwykle", "zazwyczaj", "często", "rzadko", "czasem", "niekiedy", "może", "mogą", "może być",
    "prawdopodobnie", "przypuszczalnie", "raczej", "niektór", "większość", "mniejszość", "wyłącznie",
    "tylko", "jedynie", "głównie", "przede wszystkim", "w pewnym stopniu", "do pewnego stopnia",
    "nie zawsze", "nie wszyscy", "według", "zdaniem", "podobno", "rzekomo", "szacuje się", "wydaje się",
    "potencjalnie", "ograniczon", "zastrzeż",
]

# Corrective framings (new since mid-2026, see thread / Wikipedia signs).
CORRECTIVE = [
    "należy traktować jako", "a nie jako", "nie przesądza o", "nie dowodzi, że",
    "nie należy mylić", "nie oznacza to, że", "nie chodzi o to, że",
]

# Vague associations and source-name-dropping.
VAGUE_LINKS = ["związany z", "związana z", "związane z", "w związku z",
               "kojarzony z", "powiązany z"]
SOURCE_DROP = ["odnotowan", "wzmiankowan", "udokumentowan", "opisywan w",
               "prezentowan w", "wymienian w"]


@dataclass
class Metrics:
    words: int
    sentences: int
    sent_len_mean: float
    sent_len_stdev: float
    sent_len_cv: float  # coefficient of variation: low = monotonous rhythm
    sent_len_min: int
    sent_len_max: int
    ttr: float  # type/token ratio (lexical diversity)
    em_dash_per100: float  # U+2014
    en_dash_per100: float  # U+2013 (Polish half-pause)
    hyphen_as_dash: int  # " - " used as a dash
    ktory_per100: float
    gptisms_per100: float
    gptisms_found: list[str] = field(default_factory=list)
    corrective_found: list[str] = field(default_factory=list)
    vague_links_found: list[str] = field(default_factory=list)
    source_drop_found: list[str] = field(default_factory=list)
    typography: dict[str, int] = field(default_factory=dict)
    bold_runs: int = 0
    emoji: int = 0
    rule_of_three: int = 0
    commas_per100: float = 0.0
    parens_per100: float = 0.0
    punct_other_share: float = 0.0  # share of punctuation that is not , or . (AI: lower)
    punct_entropy: float = 0.0  # Shannon entropy (bits) over punctuation types (AI: lower)


def words_of(text: str) -> list[str]:
    return WORD_RE.findall(text)


def sentences_of(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text.strip())
    return [s for s in SENT_SPLIT_RE.split(flat) if s.strip()]


def per100(count: int, words: int) -> float:
    return round(100.0 * count / words, 2) if words else 0.0


def find_phrases(text_lower: str, phrases: list[str]) -> list[str]:
    return [p for p in phrases if p in text_lower]


def typography(text: str) -> dict[str, int]:
    return {
        "quote_open_PL_U201E": text.count("\u201e"),
        "quote_close_PL_U201D": text.count("\u201d"),
        "quote_wrong_U201C": text.count("\u201c"),
        "quote_straight_U0022": text.count('"'),
        "em_dash_U2014": text.count("\u2014"),
        "en_dash_U2013": text.count("\u2013"),
        "zero_width_or_nbsp": sum(text.count(c) for c in "\u200b\u200c\u200d\ufeff\u00a0"),
        "paragraphs_leading_space": len(re.findall(r"(?m)^[ \t\u00a0]+\S", text)),
    }


PUNCT_CLASSES = {
    ",": ",", ".": ".", "…": "...", ";": ";", ":": ":", "?": "?", "!": "!",
    "(": "()", ")": "()", "\u2014": "dash", "\u2013": "dash",
    "\u201e": "quote", "\u201d": "quote", "\u201c": "quote", '"': "quote", "«": "quote", "»": "quote",
}


def punct_profile(text: str) -> tuple[int, int, float, float]:
    """(commas, paren pairs, share of non-,./ punctuation, entropy in bits)."""
    classes = [PUNCT_CLASSES[c] for c in text if c in PUNCT_CLASSES]
    # " - " used as a dash counts as dash punctuation too
    classes += ["dash"] * len(re.findall(r"\s-\s", text))
    total = len(classes)
    if not total:
        return 0, 0, 0.0, 0.0
    counts = {c: classes.count(c) for c in set(classes)}
    other = total - counts.get(",", 0) - counts.get(".", 0)
    entropy = -sum((n / total) * math.log2(n / total) for n in counts.values())
    return counts.get(",", 0), counts.get("()", 0) // 2, other / total, entropy


def analyze(text: str) -> Metrics:
    ws = words_of(text)
    n = len(ws)
    sents = sentences_of(text)
    lens = [len(words_of(s)) for s in sents] or [0]
    mean = statistics.fmean(lens)
    stdev = statistics.pstdev(lens) if len(lens) > 1 else 0.0
    low = text.lower()
    gpt = find_phrases(low, GPTISMS)
    commas, parens, other_share, entropy = punct_profile(text)
    return Metrics(
        words=n,
        sentences=len(sents),
        sent_len_mean=round(mean, 1),
        sent_len_stdev=round(stdev, 1),
        sent_len_cv=round(stdev / mean, 2) if mean else 0.0,
        sent_len_min=min(lens),
        sent_len_max=max(lens),
        ttr=round(len({w.lower() for w in ws}) / n, 3) if n else 0.0,
        em_dash_per100=per100(text.count("\u2014"), n),
        en_dash_per100=per100(text.count("\u2013"), n),
        hyphen_as_dash=len(re.findall(r"\s-\s", text)),
        ktory_per100=per100(len(KTORY_RE.findall(text)), n),
        gptisms_per100=per100(sum(low.count(p) for p in gpt), n),
        gptisms_found=gpt,
        corrective_found=find_phrases(low, CORRECTIVE),
        vague_links_found=find_phrases(low, VAGUE_LINKS),
        source_drop_found=find_phrases(low, SOURCE_DROP),
        typography=typography(text),
        bold_runs=len(re.findall(r"\*\*[^*]+\*\*", text)),
        emoji=len(re.findall(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", text)),
        rule_of_three=len(re.findall(r"\w+, \w+ (?:i|oraz) \w+", text)),
        commas_per100=per100(commas, n),
        parens_per100=per100(parens, n),
        punct_other_share=round(other_share, 3),
        punct_entropy=round(entropy, 2),
    )


def norm_words(text: str) -> set[str]:
    return {w.lower().strip("'-") for w in words_of(text) if len(w) > 1}


def fabrication_candidates(before: str, after: str) -> dict[str, list[str]]:
    """Facts-like tokens present in AFTER but not in BEFORE."""
    b_low = before.lower()
    b_words = norm_words(before)

    def novel(items: list[str]) -> list[str]:
        return sorted({i.strip() for i in items if i.strip().lower() not in b_low})

    nums = novel(NUMBER_RE.findall(after)) + sorted(
        {w.lower() for w in NUMERAL_RE.findall(after) if w.lower()[:4] not in {x[:4] for x in b_low.split()}}
    )
    urls = novel(URL_RE.findall(after))
    quotes = novel(QUOTE_RE.findall(after))
    def stem(w: str) -> str:
        w = w.lower().rstrip("-")
        return w[: max(4, len(w) - 3)]  # crude Polish inflection: Małopolski ~ Małopolsce

    b_stems = {stem(w) for w in b_words}
    # Words opening a sentence (after optional quote/bracket) are not proper-noun evidence.
    sentence_initial = {
        re.sub(r"^[„\"«(\[*]+", "", s).split()[0].strip("*,.;:")
        for s in sentences_of(after) if s.split()
    }
    proper = {
        p for p in PROPER_RE.findall(after)
        if stem(p) not in b_stems and p not in sentence_initial
    }
    # Sentence-initial brand names (GitHub, OpenAI, PKP) are skipped by
    # PROPER_RE; catch CamelCase / ALL-CAPS tokens regardless of position.
    proper |= {
        w for w in words_of(after)
        if (re.search(r"[a-ząćęłńóśźż][A-ZĄĆĘŁŃÓŚŹŻ]", w) or (w.isupper() and len(w) > 2))
        and stem(w) not in b_stems
    }
    proper = sorted(proper)
    return {"numbers": nums, "proper_nouns": proper, "quotes": quotes, "urls": urls}


def dropped_qualifiers(before: str, after: str) -> list[str]:
    """Hedges/quantifiers present in BEFORE and absent from AFTER (scope or modality changed)."""
    b_low, a_low = before.lower(), after.lower()
    return [q for q in QUALIFIERS if re.search(r"\b" + re.escape(q), b_low) and not re.search(r"\b" + re.escape(q), a_low)]


def novel_content_share(before: str, after: str) -> float:
    """Share of content words (>=5 chars) in AFTER whose 5-char stem is absent from BEFORE.
    High values on a short example mean the 'Po' says things the 'Przed' did not."""
    stem = lambda w: w.lower()[:5]  # noqa: E731
    b = {stem(w) for w in words_of(before) if len(w) >= 5}
    a = [stem(w) for w in words_of(after) if len(w) >= 5]
    return round(sum(1 for s in a if s not in b) / len(a), 2) if a else 0.0


def punct_delta(before: str, after: str) -> dict[str, float]:
    """Per-100-word change of dash-like and comma punctuation (after - before)."""
    mb, ma = analyze(before), analyze(after)
    dashes = lambda m: m.em_dash_per100 + m.en_dash_per100 + per100(m.hyphen_as_dash, m.words)  # noqa: E731
    return {"dashes": round(dashes(ma) - dashes(mb), 2), "commas": round(ma.commas_per100 - mb.commas_per100, 2)}


def punct_delta_abs(before: str, after: str) -> dict[str, int]:
    """Absolute change of dash-like marks and commas (after - before); for short texts."""
    cnt = lambda t: t.count("\u2014") + t.count("\u2013") + len(re.findall(r"\s-\s", t))  # noqa: E731
    return {"dashes": cnt(after) - cnt(before), "commas": after.count(",") - before.count(",")}


def diff_report(before: str, after: str) -> dict:
    b, a = norm_words(before), norm_words(after)
    union = b | a
    a_low, b_low = after.lower(), before.lower()
    introduced = sorted(g for g in GPTISMS if g in a_low and g not in b_low)
    return {
        "introduced_gptisms": introduced,
        "word_count_ratio": round(len(words_of(after)) / max(1, len(words_of(before))), 2),
        "jaccard_vocab": round(len(b & a) / len(union), 3) if union else 1.0,
        "share_of_after_vocab_new": round(len(a - b) / len(a), 3) if a else 0.0,
        "share_of_before_vocab_dropped": round(len(b - a) / len(b), 3) if b else 0.0,
        "fabrication_candidates": fabrication_candidates(before, after),
        "punct_delta_per100": punct_delta(before, after),
        "punct_delta_abs": punct_delta_abs(before, after),
        "dropped_qualifiers": dropped_qualifiers(before, after),
        "novel_content_share": novel_content_share(before, after),
    }


def strip_markdown_quote(text: str) -> str:
    """Allow pasting '> ' blockquote blocks straight from SKILL.md."""
    return re.sub(r"(?m)^>\s?", "", text)


def fmt_table(name: str, m: Metrics) -> str:
    rows = [
        ("słowa / zdania", f"{m.words} / {m.sentences}"),
        ("dł. zdania śr ± sd (CV)", f"{m.sent_len_mean} ± {m.sent_len_stdev} ({m.sent_len_cv})"),
        ("dł. zdania min–max", f"{m.sent_len_min}–{m.sent_len_max}"),
        ("TTR", f"{m.ttr}"),
        ("— (U+2014) /100 słów", f"{m.em_dash_per100}"),
        ("– (U+2013) /100 słów", f"{m.en_dash_per100}"),
        ("' - ' jako myślnik", f"{m.hyphen_as_dash}"),
        ("który* /100 słów", f"{m.ktory_per100}"),
        ("GPT-izmy /100 słów", f"{m.gptisms_per100} {m.gptisms_found}"),
        ("corrective framings", f"{m.corrective_found}"),
        ("mgliste powiązania", f"{m.vague_links_found}"),
        ("name-dropping źródeł", f"{m.source_drop_found}"),
        ("przecinki /100 słów", f"{m.commas_per100}"),
        ("nawiasy /100 słów", f"{m.parens_per100}"),
        ("interp. inna niż , . (udział)", f"{m.punct_other_share:.1%}"),
        ("entropia interpunkcji (bity)", f"{m.punct_entropy}"),
        ("bold / emoji / reguła 3", f"{m.bold_runs} / {m.emoji} / {m.rule_of_three}"),
        ("typografia", json.dumps(m.typography, ensure_ascii=False)),
    ]
    width = max(len(r[0]) for r in rows)
    return f"== {name} ==\n" + "\n".join(f"{k.ljust(width)}  {v}" for k, v in rows)


# --- SKILL.md frontmatter lint -------------------------------------------

RISKY_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "Bash", "WebFetch", "WebSearch"}
# Fields accepted by claude.ai upload / Skills API / package_skill.py.
PORTABLE_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
AUTO_TRIGGER_RE = re.compile(r"\b(zawsze|always|whenever|każd\w*|any)\b", re.IGNORECASE)


def parse_frontmatter(text: str) -> dict[str, str]:
    """Minimal YAML-ish parser: top-level 'key: value' and '>' / '|' blocks."""
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fields: dict[str, str] = {}
    key = None
    for line in m.group(1).splitlines():
        if re.match(r"^[\w-]+:", line):
            key, _, val = line.partition(":")
            fields[key.strip()] = val.strip().lstrip(">|").strip()
        elif key and line.startswith((" ", "\t")):
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def lint_skill(path: Path) -> list[str]:
    fm = parse_frontmatter(path.read_text(encoding="utf-8"))
    if not fm:
        return ["ERROR: no YAML frontmatter found"]
    msgs: list[str] = []
    tools = set(re.split(r"[,\s]+", fm.get("allowed-tools", "").strip()) if fm.get("allowed-tools") else [])
    tools.discard("")
    risky = sorted(tools & RISKY_TOOLS)
    auto_invocable = fm.get("disable-model-invocation", "").lower() != "true"
    if risky:
        level = "ERROR" if auto_invocable else "WARN"
        msgs.append(
            f"{level}: allowed-tools grants {risky} without per-use approval"
            + (" and the skill can be auto-invoked by the model" if auto_invocable else "")
            + " (prompt injection in edited text -> silent file writes/commands)"
        )
    if auto_invocable and AUTO_TRIGGER_RE.search(fm.get("description", "")):
        msgs.append("WARN: description contains broad trigger words (zawsze/always/każdy); "
                    "the model may auto-activate the skill on any Polish text")
    for k in sorted(set(fm) - PORTABLE_FIELDS):
        msgs.append(f"INFO: field '{k}' is Claude Code-only; claude.ai upload / Skills API reject it with a hard error")
    if "disable-model-invocation" not in fm and risky:
        msgs.append("INFO: Claude Code-only mitigation: disable-model-invocation: true (manual /command only)")
    return msgs or ["OK: frontmatter has no risky tool grants"]


def percentile_rank(value: float, pcts: dict[str, float]) -> str:
    """Coarse position of value within reference percentiles (p5..p95)."""
    if not pcts:
        return "n/a"
    order = sorted((int(k[1:]), v) for k, v in pcts.items())
    if value < order[0][1]:
        return f"<p{order[0][0]}"
    for (lo_p, lo_v), (hi_p, hi_v) in zip(order, order[1:]):
        if lo_v <= value <= hi_v:
            return f"p{lo_p}–p{hi_p}"
    return f">p{order[-1][0]}"


def ref_table(name: str, m: dict, ref: dict) -> str:
    human = ref.get("human", {})
    lines = [f"== {name} vs human reference ({ref.get('source', '?')}, n={ref.get('n', {}).get('human')}) =="]
    for f, pcts in human.items():
        if f in m and pcts:
            lines.append(f"{f.ljust(20)} {str(m[f]).ljust(8)} {percentile_rank(m[f], pcts).ljust(9)} "
                         f"(p5 {pcts['p5']} | p50 {pcts['p50']} | p95 {pcts['p95']})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("before", type=Path, help="text file, or SKILL.md with --lint-skill")
    ap.add_argument("after", type=Path, nargs="?")
    ap.add_argument("--baseline", type=Path, help="author's own human text for calibration")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--skill", type=Path, default=Path(__file__).resolve().parent.parent / "SKILL.md",
                    help="SKILL.md whose §30/§31 lists define GPT-isms (default: repo SKILL.md)")
    ap.add_argument("--ref", type=Path, help="reference percentiles JSON from build_reference.py")
    ap.add_argument("--lint-skill", action="store_true", help="lint SKILL.md frontmatter for risky tool grants")
    args = ap.parse_args(argv)

    if args.skill and args.skill.exists():
        GPTISMS[:] = load_skill_phrases(args.skill)
    if args.lint_skill:
        msgs = lint_skill(args.before)
        print("\n".join(msgs))
        return 1 if any(m.startswith("ERROR") for m in msgs) else 0

    read = lambda p: strip_markdown_quote(p.read_text(encoding="utf-8"))  # noqa: E731
    out: dict = {"before": asdict(analyze(read(args.before)))}
    if args.after:
        out["after"] = asdict(analyze(read(args.after)))
        out["diff"] = diff_report(read(args.before), read(args.after))
    if args.baseline:
        out["baseline"] = asdict(analyze(read(args.baseline)))

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    ref = json.loads(args.ref.read_text(encoding="utf-8")) if args.ref else None
    src = args.skill if args.skill and args.skill.exists() else "built-in fallback"
    print(f"[GPT-izmy: {len(GPTISMS)} fraz z {src}]\n")
    for key in ("baseline", "before", "after"):
        if key in out:
            print(fmt_table(key, Metrics(**out[key])), end="\n\n")
            if ref:
                print(ref_table(key, out[key], ref), end="\n\n")
    if "diff" in out:
        d = out["diff"]
        print("== diff before -> after ==")
        print(f"stosunek długości          {d['word_count_ratio']}")
        print(f"Jaccard słownictwa          {d['jaccard_vocab']}")
        print(f"słownictwo nowe w AFTER     {d['share_of_after_vocab_new']:.0%}")
        print(f"słownictwo BEFORE utracone  {d['share_of_before_vocab_dropped']:.0%}")
        fc = d["fabrication_candidates"]
        flagged = {k: v for k, v in fc.items() if v}
        if flagged:
            print("⚠️ kandydaci na dopisane fakty (są w AFTER, brak w BEFORE) – każdy wymaga potwierdzenia użytkownika:")
            for k, v in flagged.items():
                print(f"  {k}: {v}")
        else:
            print("✅ brak nowych liczb, nazw własnych, cytatów ani URL-i")
        pd = d["punct_delta_per100"]
        print(f"Δ myślniki /100: {pd['dashes']:+.2f}   Δ przecinki /100: {pd['commas']:+.2f}")
        if d["dropped_qualifiers"]:
            print(f"⚠️ kwantyfikatory/zastrzeżenia usunięte z BEFORE: {d['dropped_qualifiers']}")
        print(f"udział nowych słów treściowych w AFTER: {d['novel_content_share']:.0%}")
        if d["introduced_gptisms"]:
            print(f"⚠️ GPT-izmy wprowadzone przez redakcję (brak w BEFORE): {d['introduced_gptisms']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
