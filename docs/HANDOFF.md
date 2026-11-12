# Handoff

Read at the start of every phase. At the end of each phase, **replace** the "Latest handoff" section with the new one (template below) and add one line to "History". Keep this file short. Details belong in commits and `docs/results.md`.

## Latest handoff

**Phase:** 08-dense-hybrid
**Date:** 2026-11-12
**Status:** done

**Done**
- torch from the `cu128` index on Windows (driver reports CUDA 13.5; `torch 2.11.0+cu128`, `cuda.is_available()` True on the RTX 3060 Ti), CPU index on Linux. `embed.py`, `retrieve.py` (`dense_search`, `rrf`), `build-index --embed`, `--mode bm25|dense|hybrid` on `search` and `eval-retrieval`, `Index.embeddings`. Default mode is now `hybrid` (PLAN.md edited).
- Index `2026-11-11-v2` built: 868 chunks, `chunk_id`s identical to v1, `embeddings.npy` (868, 1024), **embedding took 133 s on the GPU** (the plan said 15-30 min). `eval/index_version.txt` = `2026-11-11-v2`.
- Thresholds ratcheted from the hybrid test summaries; `check-thresholds` passes. 95 tests passed (incl. slow), ruff clean.

**Deviations from plan**
- `pipeline` imports `embed` lazily (inside the dense branch) so BM25-only paths and fast tests don't import torch.
- `eval-retrieval` and `search` CLI default `--mode` is now `hybrid` (was bm25).

**Metrics** (test split unless stated; index `2026-11-11-v2`)

| run | recall@5 | recall@20 | mrr@10 |
|---|---|---|---|
| bm25 (v1) | 81% | 88% | 0.64 |
| dense | 88% | 100% | 0.71 |
| hybrid | 88% | 100% | 0.71 |
| hybrid, dev | 94% | 97% | 0.90 |
| bm25 xling (v1) | 6% | 6% | 0.06 |
| dense xling | 94% | 100% | 0.88 |
| hybrid xling | 94% | 100% | 0.88 |

Answers, hybrid test (gen `gpt-6-luna`, judge `gpt-6.1-terra`): refusal 90% (was 85), lang 100%, cite valid 100%, faithfulness 100% (was 92), correctness 50% (was 54), citation accuracy 100% (was 92); p95 2269 ms; failed refusal q022, q037; gen $0.00018/q.

New thresholds (test): recall@5 0.80, mrr@10 0.65, refusal_correct 0.85, lang_match 0.95, faithfulness 0.95, citation_accuracy 0.95.

**What it shows:** dense retrieval fixes BM25's cross-lingual blind spot (xling recall@5 6% to 94%) and lifts same-language recall too. On this small test set hybrid equals dense overall (88% / 0.71 for both, though per-language rows differ), so RRF's gain over dense alone is not demonstrated here. Dev hybrid (94% / 0.90) is the larger sample.

**OpenAI spend:** $0.036 this phase (answer eval test: judge $0.0325 + gen $0.0037) / ~$0.155 cumulative of $5. Retrieval evals use no OpenAI.

**Open issues**
- All 60 questions are still `llm_assisted`, gold labels unreviewed. The test split is 20 questions, so one question moves recall by about 6 points; read "hybrid == dense" and the xling number (94%, above same-language 88%) with that in mind. Xling is higher partly because the language filter limits search to a smaller pool.
- Correctness 50% still reflects judge strictness on key facts (not gated, D37). Over-refusals q022, q037 remain (phase 09 gate).
- Dense-only was not run on dev, so there is no dev dense vs hybrid comparison.
- TDRA permission still pending; phases 15-16 stay gated.

**Notes for next phase**
- Index version in use: `2026-11-11-v2`. `embeddings.npy` is local only (gitignored); CI cannot run hybrid until phase 15 uploads the index.
- The HF warning about `HF_TOKEN` is harmless.
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
