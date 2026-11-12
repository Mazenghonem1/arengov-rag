# Handoff

Read at the start of every phase. At the end of each phase, **replace** the "Latest handoff" section with the new one (template below) and add one line to "History". Keep this file short. Details belong in commits and `docs/results.md`.

## Latest handoff

**Phase:** 06-retrieval-eval
**Date:** 2026-11-12
**Status:** done

**Done**
- `eval_retrieval.py` (`hit_at`, `rr_at`, `run`), CLI `eval-retrieval [--split --label --mode --cross-lingual --no-norm --no-rerank --record --out]`, `docs/results.md`, `tests/test_eval_retrieval.py`.
- 4 baseline runs recorded; summaries in `eval/results/*.json` (committed), details in `eval/results/details/` (gitignored).

**Deviations from plan**
- `run` also takes `out=` (the `--out` CLI option). Answerable questions are 34 on dev and 16 on test (6 and 4 unanswerable excluded).
- mrr@10 is shown as a 0-1 score in `results.md`, not a percentage.

**Metrics** (BM25, index `2026-11-11-v1`)

| label | split | n | recall@5 | recall@20 | mrr@10 |
|---|---|---|---|---|---|
| bm25-baseline | dev | 34 | 91% | 97% | 0.78 |
| bm25-baseline | test | 16 | 81% | 88% | 0.64 |
| bm25-xling | test | 16 | 6% | 6% | 0.06 |
| bm25-nonorm | test | 16 | 75% | 88% | 0.65 |

- Cross-lingual is near 0 as expected. The one hit (q059) is a mixed-script English question containing the Arabic word "تصريح عمل", which matches Arabic chunks. Not a mask bug.
- Normalization helps Arabic on test (recall@5 62% -> 75% for ar, 1 question = 12.5 points) and does nothing for English. n=8, so treat as a hint.
- tests: 74 passed (1 deselected as slow), ruff clean.

**5 worst dev misses** (3 true recall@5 misses, 2 low-rank hits)
1. q032 (ar) "how do I know if a trade name is available" -> gold National Economic Register; top-3 are business-setup pages. Vocabulary mismatch: the gold page is about the register, the query says "trade name".
2. q038 (en, multi-turn) "What salary do I need for that?" -> gold Residence visa for families; top-3 are salary/wages pages. The last turn alone lacks the referent from the earlier turn. Needs rewriting (phase 10).
3. q045 (ar, multi-turn) "where do I file the complaint?" -> gold Payment of wages; top-3 are labour-dispute pages. Same cause: context lost; the gold choice is also arguable (disputes pages are plausible answers).
4. q057 (ar, mixed) "overtime percentage in private companies" -> gold Working hours and overtime at rank 4; top-3 are company-setup pages. The English word "overtime" can't match Arabic chunks, so only "private companies" matches. Cross-script/vocabulary.
5. q023 (ar) "minimum working age in UAE" -> gold Employing minors at rank 3; "UAE/Emirates"-heavy company pages outrank it. Common-word noise; dense retrieval should help.

**OpenAI spend:** $0 this phase / ~$0.0005 cumulative

**Open issues**
- Test split is 16 answerable questions: 1 question = 6 points, so differences under ~12 points are noise.
- q045's gold label may be too narrow (owner review of llm_assisted labels still pending).
- TDRA: no written permission yet; phases 15-16 stay gated.

**Notes for next phase**
- Phase 07 reuses `eval/results/` naming and appends to the same `docs/results.md` table (answer columns).
- Index version in use: `2026-11-11-v1`.
- Carried over: citation dedup (phase 13); `Types-of-visas` vs `residence-visas` duplicate URLs.

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
| 06 retrieval-eval | 2026-11-12 | done | BM25 recall@5 91% dev / 81% test; xling 6% |
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
