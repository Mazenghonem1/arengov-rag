# Handoff

Read at the start of every phase. At the end of each phase, **replace** the "Latest handoff" section with the new one (template below) and add one line to "History". Keep this file short. Details belong in commits and `docs/results.md`.

## Latest handoff

**Phase:** 11-judge-validation
**Date:** 2026-11-13
**Status:** partial: Part A done, waiting on [YOU] grading

**Done (Part A)**
- `judge.export_blind` + CLI `judge-export`; 45 items (test + dev `rewrite` details, both judged by `gpt-6.1-terra`) written to gitignored `eval/grading/` (`items.md`, `grades.csv`, `key.json`). Test added; 103 tests pass, ruff clean.

**OpenAI spend:** $0 this phase so far / about $0.31 cumulative of $5.

**Next:** owner fills `eval/grading/grades.csv` (1/0 per criterion, blind), then new session on this branch: "phase 11 Part B".

## History

| Phase | Date | Result | Key metric |
|---|---|---|---|
| planning | 2026-11-09 | done | — |
| 00 setup | 2026-11-09 | done | CI green |
| 01 crawl | 2026-11-11 | done | 145 EN / 143 AR pages |
| 02 clean-chunk | 2026-11-11 | done | 868 chunks (419 EN / 449 AR), max 400 tokens |
| 03 bm25 | 2026-11-11 | done | BM25 build 4.3 s, 41 tests |
| 04 generate | 2026-11-11 | done | ~$0.00016 / OpenAI query, 50 tests |
| 05 eval-set | 2026-11-12 | done | 60 questions (40 dev / 20 test), 72 tests |
| 06 retrieval-eval | 2026-11-12 | done | BM25 recall@5 91% dev / 81% test; xling 6% |
| 07 answer-eval | 2026-11-12 | done | faithfulness 91% dev / 92% test, correctness 56% / 54%; $0.12 |
| 08 dense-hybrid | 2026-11-12 | done | hybrid recall@5 88% test / 94% dev, xling 94%; $0.04 |
| 09 rerank-gate | 2026-11-12 | done* | tau 0.298 (dev F1 0.83), test mrr@10 0.82; $0.04 |
| 10 multiturn | 2026-11-13 | done | multi-turn recall@5 test 33% -> 67%, dev 100%; $0.12 |
---

## Template (copy into "Latest handoff")

```
**Phase:** NN-name
**Date:** YYYY-MM-DD
**Status:** done | partial (Part A done, waiting on [YOU] …)

**Done**
- …

**Deviations from plan** (what changed vs the phase file, and why; contract changes also edited in PLAN.md)
- …

**Metrics** (copy the rows this phase added to docs/results.md; tests: N passed)
- …

**OpenAI spend** (this phase / cumulative vs the $5 credit; estimate in PLAN.md § Estimated OpenAI spend)
- $… / $…

**Open issues** (bugs, risks, anything left undone, with an owner)
- …

**Notes for next phase**
- … (facts the next session needs that aren't in the repo: index_version in use, τ value, model quirks, commands that were slow)

**Commit:** <short sha> <message>
```
