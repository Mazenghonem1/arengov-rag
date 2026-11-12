# Handoff

Read at the start of every phase. At the end of each phase, **replace** the "Latest handoff" section with the new one (template below) and add one line to "History". Keep this file short. Details belong in commits and `docs/results.md`.

## Latest handoff

**Phase:** 07-answer-eval
**Date:** 2026-11-12
**Status:** done

**Done**
- `judge.py`, `eval_answers.py` (`run`, `rejudge`, `set_thresholds`, `check_thresholds`), CLI `eval-answers`, `set-thresholds`, `check-thresholds`; tests in `test_judge.py`, `test_eval_answers.py`, `test_thresholds.py` (90 passed, ruff clean).
- BM25 answer baseline recorded for dev and test; `eval/thresholds.json` written from the test split; `check-thresholds` passes on the phase-06 and phase-07 test summaries.

**Deviations from plan**
- `pipeline.answer` also returns `invalid_citations` (PLAN.md edited): `citation_valid` needs it because `parse_citations` strips out-of-range markers from the text.
- `run`/`rejudge` also take `out=`. `eval_cost_usd` is judge cost only; `gen_cost_usd` is stored separately.
- Ollama smoke run skipped: the judge always uses OpenAI, so there is no free end-to-end run.

**Metrics** (BM25, index `2026-11-11-v1`, gen `gpt-6-luna`, judge `gpt-6.1-terra`)

| split | n | judged | refusal | lang | cite valid | faithful | correct | cite acc | p95 ms | $/q |
|---|---|---|---|---|---|---|---|---|---|---|
| dev | 40 | 32 | 95% | 100% | 100% | 91% | 56% | 94% | 1827 | $0.00019 |
| test | 20 | 13 | 85% | 100% | 100% | 92% | 54% | 92% | 1994 | $0.00017 |

Thresholds (test): recall@5 0.75, mrr@10 0.55, refusal_correct 0.80, lang_match 0.95, faithfulness 0.85, citation_accuracy 0.85. `correctness` is not gated (D37).

**Top 5 dev failures** (the full list is in the dev details file)
1. **Judge strictness on key facts (q004, q008, q011, q019, q025, q030, q044, q046 and others: 14 of 32 fail correctness).** Answers are short and correct but omit a secondary key fact (e.g. q030 names the regulator but not the example platforms). Not a pipeline bug. The key facts were written by Claude, so owner review (phase 11) decides whether they are too demanding. Read the 56% as a floor, not as quality.
2. **Over-refusal (q007, q010; test q005, q022, q037).** The gold page is already in the top 3 chunks, yet the generator answers NO_ANSWER. Cause: generator or prompt over-caution, not retrieval. Worth testing a different prompt or the rerank gate (phase 09).
3. **Retrieval miss (q032, q023, q046).** Gold page not in the top 5 or crowded out ("trade name" vs National Economic Register; "UAE" noise). The answer then comes from a wrong page, so correctness fails. Dense retrieval (phase 08) should help.
4. **Multi-turn context lost (q038, q040, q041, q044, q046).** The last turn alone has no referent, so retrieval and answer drift (q038 answers about virtual work visas; q041 fabricates a free-zone timing). Fixed by rewriting in phase 10.
5. **Slight unfaithfulness (q016, q041, q038).** Small unsupported additions ("specified in your contract", "per month", merged timeframes). Rare: 3 of 32. Two of the three come with multi-turn context loss.

**OpenAI spend:** $0.118 this phase (dev: judge $0.077 + gen $0.008; test: judge $0.030 + gen $0.003) / ~$0.119 cumulative of $5. Under the $0.24 estimate; the test run's `eval_cost_usd` was $0.030 (limit $0.15).

**Open issues**
- All gold labels and key facts are `llm_assisted` and unreviewed; the correctness numbers and the thresholds depend on them.
- Test split is 20 questions (13 judged): one question moves a rate by 5-8 points.
- TDRA: no written permission yet; phases 15-16 stay gated.
- q045 gold label may be too narrow (carried over).

**Notes for next phase**
- Phase 08 answer eval on test costs about $0.04, not $0.08 (measured). The PLAN estimates are about 2x too high.
- `set-thresholds` ratchets: re-running it with worse numbers never lowers a gate.
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
| 07 answer-eval | 2026-11-12 | done | faithfulness 91% dev / 92% test, correctness 56% / 54%; $0.12 |
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
