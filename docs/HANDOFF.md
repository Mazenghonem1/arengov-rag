# Handoff

Read at the start of every phase. At the end of each phase, **replace** the "Latest handoff" section with the new one (template below) and add one line to "History". Keep this file short. Details belong in commits and `docs/results.md`.

## Latest handoff

**Phase:** 05-eval-set
**Date:** 2026-11-12
**Status:** done (Part A + B in one session; questions written by Claude, not the owner)

**Done**
- `evalset.py` (`sample_pages`, `validate`, `assign_splits`, plus `count_table`), CLI `sample-pages`, `validate-eval [--strict]`, `assign-splits`.
- `eval/README.md` labeling guide, empty `eval/questions.jsonl`, `tests/test_evalset.py`.

**Deviations from plan**
- The owner asked Claude to write the 60 questions. All have `origin: "llm_assisted"`, written from the cleaned page text of index `2026-11-11-v1`, so phrasing may be biased toward LLM style. Owner should review them (especially the 6 `unanswerable_near` and the gold labels) before relying on test numbers.
- Numbers in key facts and reference answers were checked automatically against the gold pages' text; the other facts were checked by reading, not by script.
- Several gold labels list two page_ids: `golden-visa` (exists under `types-of-visas/` with an AR twin, and under `residence-visas/` EN only) and `employing-minors` (EN-only duplicate `employment-and-training-of-minors`).

**Metrics:** tests: 72 passed (1 deselected as slow), ruff clean. `validate-eval --strict` passes.

| type | lang | dev | test |
|---|---|---|---|
| single | ar / en | 12 / 12 | 6 / 6 |
| multi_turn | ar / en | 3 / 4 | 2 / 1 |
| unanswerable_near | ar / en | 2 / 2 | 1 / 1 |
| unanswerable_oos | ar / en | 1 / 1 | 1 / 1 |
| mixed_script | ar / en | 2 / 1 | 0 / 1 |

Spot-check (BM25 `search`, last turn, top 10; preview only): 5 of 5 had a gold page in the top 10 (q017 rank 1, q058 rank 1, q023 rank 3, q040 rank 3, q045 rank 7).

**OpenAI spend:** $0 this phase / ~$0.0005 cumulative

**Open issues**
- Some pages exist in only one language (e.g. golden-visa has no AR pair in the sample); `sample-pages` shows "—" for those.
- TDRA: no written permission yet; phases 15-16 stay gated.

**Notes for next phase**
- Splits come from `assign-splits --seed 13`; re-running it after editing questions changes them, so edit questions first.
- The test split has only 20 questions: 1 question = 5 points.
- Index version in use: `2026-11-11-v1`.
- Carried over from phase 04: citations for the same page are listed separately (consider dedup in phase 13); `Types-of-visas` vs `residence-visas` duplicate URLs.

**Commit:** see PR

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
