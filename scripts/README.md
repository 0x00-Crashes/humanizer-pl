# scripts/metrics.py

Objective metrics for humanizer-pl output. Pure stdlib, Python 3.11+.

```
python3 scripts/metrics.py before.md after.md          # metrics + diff + fabrication candidates
python3 scripts/metrics.py before.md after.md --json
python3 scripts/metrics.py text.md --baseline my_own_text.md
python3 scripts/metrics.py SKILL.md --lint-skill       # frontmatter: risky allowed-tools, auto-trigger description
```

## What it does and does not tell you

- **Fabrication candidates** (numbers, proper nouns, quotes, URLs present in
  `after` but not in `before`) are *candidates*. Each one needs a human
  decision: a genuine fix of wrong realia (e.g. a corrected company name, §34)
  also shows up here. The script never reverts anything.
- Densities per 100 words have **no built-in thresholds**. Calibrate with
  `--baseline` on the author's own human-written text; values depend on
  author, genre and model generation.
- Proper-noun detection is a heuristic (capitalised non-initial words,
  CamelCase, ALL-CAPS >2 chars). Expect occasional false positives.
- Sentence splitting is regex-based; bullet lists and abbreviations ("np.")
  skew sentence-length stats. Compare prose with prose.
- `--lint-skill` exit code 1 = `allowed-tools` grants write/exec tools while the
  skill can be auto-invoked. `disable-model-invocation` is Claude Code-only;
  for portable skills (claude.ai, Skills API) narrow `allowed-tools` and the
  `description` instead.

## Caveat on the numbers in the discussion

Running this on the "Pełny przykład" from `SKILL.md` measures the
**documentation**, i.e. what the hand-written example teaches the model, not
what the skill actually produces at runtime. A real measurement needs N
Polish texts (e.g. human samples from `poleval/2025-smigiel`) passed through
the skill on Claude, then `metrics.py` on each pair.

## Reference percentiles (`--ref`)

`scripts/build_reference.py <2025-smigiel>/data/train` writes
`reference/smigiel.json`: p5/p25/p50/p75/p95 for every density on the 5247
human texts (>=100 words) of PolEval 2025 Śmigiel, with the AI column kept for
context only. `metrics.py A B --ref reference/smigiel.json` then prints where
each value sits among human texts. Note that Śmigiel is mostly web/encyclopedic
prose; for a thesis or a blog, build a baseline from the author's own texts.
Also note `em_dash_per100` p95 = 0.0 in human Śmigiel: Polish writers use the
half-pause (U+2013), so any U+2014 at all is already an outlier there.
