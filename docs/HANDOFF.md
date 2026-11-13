# Handoff

Read at the start of every phase. At the end of each phase, **replace** the "Latest handoff" section with the new one (template below) and add one line to "History". Keep this file short. Details belong in commits and `docs/results.md`.

## Latest handoff

**Phase:** 09-rerank-gate
**Date:** 2026-11-12
**Status:** done, except `check-thresholds` fails on 2 answer metrics (see Open issues)

**Done**
- `rerank.py` (bge-reranker-v2-m3, sigmoid via `activation_fn`, sentence-transformers 6.3.0), `retrieve.collapse_pairs`, `pipeline.retrieve` reranks the top-20 then collapses translation pairs (`stages["reranked"]` added), `pipeline.answer` gates before `generate` (`refusal_reason="gate"`, no LLM call, usage 0), shared `_refusal` helper, `pick-tau` CLI (`eval_retrieval.choose_tau` / `pick_tau`).
- **`GATE_TAU = 0.298`**, picked on dev (33 questions, multi-turn excluded; 6 should-refuse): best F1 0.83 (precision 0.83, recall 0.83), refuses 1/27 answerable (q057), safety rule passes. q050 (unanswerable) scores 0.97, so only `NO_ANSWER` can catch it.
- 101 tests passed (incl. slow), ruff clean. 4 rows added to `docs/results.md`. `eval/thresholds.json`: mrr@10 0.65 -> 0.75 (ratchet).

**Deviations from plan**
- None to contracts. `pick-tau` takes only `--split` (no `--backend`: it makes no LLM calls).

**Metrics** (index `2026-11-11-v2`; phase 08 hybrid -> phase 09 rerank+collapse+gate)

| run | recall@5 | recall@20 | mrr@10 |
|---|---|---|---|
| test | 88% -> 88% | 100% -> 100% | 0.71 -> 0.82 |
| test xling | 94% -> 94% | 100% -> 100% | 0.88 -> 0.80 |
| dev | 94% -> 97% | 97% -> 97% | 0.90 -> 0.87 |

Rerank raises same-language test MRR but **lowers MRR on xling test and on dev**; recall@5 holds or rises. Test n=16, so read with care. Test multi-turn recall@5 is 33% (no rewriting until phase 10).

Answers, test (gen `gpt-6-luna`, judge `gpt-6.1-terra`; 14 judged): refusal 90% (was 90; q022 now fixed, q043 new, q037 still failing), lang 100%, cite valid 100%, faithfulness 93% (was 100), correctness 50% (was 50), citation accuracy 93% (was 100); p50/p95 1944/2890 ms; gen $0.00016/q. The one faithfulness/citation miss is q005 (answer said "either" for requirements that are cumulative), 1 of 14 judged.

**CPU rerank latency** (20 candidates, 10 queries, 12-thread desktop CPU): p50 11.9 s, p95 12.4 s. Far above the 3 s HF limit; phase 16 needs top-10 or smaller, and probably more than that.

**OpenAI spend:** $0.037 this phase (judge $0.0342 + gen $0.0032) / ~$0.192 cumulative of $5.

**Open issues**
- `check-thresholds` fails: faithfulness and citation_accuracy are 0.929 vs min 0.95, from a single judged answer (q005). Thresholds were not lowered (ratchet never lowers). Owner decision needed.
- Gold labels still all `llm_assisted`, unreviewed. Over-refusals q037, q043 remain. Multi-turn follow-ups fail until phase 10, which also re-picks tau including them.
- tau rests on only 6 unanswerable dev questions.
- TDRA permission pending; phases 15-16 gated.

**Notes for next phase**
- Index version `2026-11-11-v2`, embeddings local only. The reranker loads on GPU locally (~2-3 s per query on top of retrieval).
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
| 08 dense-hybrid | 2026-11-12 | done | hybrid recall@5 88% test / 94% dev, xling 94%; $0.04 |
| 09 rerank-gate | 2026-11-12 | done* | tau 0.298 (dev F1 0.83), test mrr@10 0.82; $0.04 |
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
