# Handoff

Read at the start of every phase. At the end of each phase, **replace** the "Latest handoff" section with the new one (template below) and add one line to "History". Keep this file short. Details belong in commits and `docs/results.md`.

## Latest handoff

**Phase:** 10-multiturn
**Date:** 2026-11-13
**Status:** done

**Done**
- `rewrite.py` (user messages only, last 3 + new one), `pipeline.answer` rewrites when there is history, retrieves and generates with the rewritten query, detects lang from the original, adds rewrite tokens/cost to `usage`.
- `eval-retrieval` and `pick-tau` take `--backend` (default `openai`) and rewrite multi-turn questions; `pick-tau` now includes multi-turn.
- **`GATE_TAU` stays 0.298**: re-picked on dev with multi-turn included (34 q), best tau 0.2983, F1 0.83, refuses 1/34 answerable (q057).
- `ui/examples.json`: en = transit visa validity (q006); ar = domestic worker leave and rest (q022, cites the English `domestic-helpers` page); ar_followup = "وهل لها تذكرة سفر؟" (rewritten correctly, answered with a citation to the English page); offtopic = UK work visa (q054, refused). Checked on OpenAI, except en/off-topic, which came from the eval details.
- 102 tests passed (not slow), ruff clean. 4 rows added to `docs/results.md`. Thresholds ratcheted: recall@5 0.80->0.85, mrr@10 0.75->0.80, refusal_correct 0.85->0.90; `check-thresholds` passes.

**Deviations from plan**
- None to contracts. Rewriter debugging on Ollama needed `REWRITE_MAX_TOKENS` raised in the debug script only: qwen3 thinks despite `/no_think` and hits 200 tokens (the code then falls back to the original question). OpenAI is unaffected (reasoning effort none).

**Metrics** (index `2026-11-11-v2`; phase 09 -> phase 10)

| run | recall@5 | recall@20 | mrr@10 | multi-turn recall@5 |
|---|---|---|---|---|
| test | 88% -> 94% | 100% -> 100% | 0.82 -> 0.88 | 33% -> 67% (n=3) |
| dev | 97% -> 97% | 97% -> 97% | 0.87 -> 0.94 | not measured -> 100% (n=7) |

Answers (gen `gpt-6-luna`, judge `gpt-6.1-terra`): test refusal 90% -> 95%, faithfulness 93% -> 100%, correctness 50% -> 53%, citation accuracy 93% -> 100% (15 judged). Dev: refusal 90%, faithfulness 100%, correctness 53%, citation accuracy 97% (30 judged). Test multi-turn refusal 67% (q043 still over-refused); dev multi-turn refusal 71%.

**OpenAI spend:** about $0.12 this phase (test answers $0.040, dev answers $0.080, retrieval rewrites and pick-tau ~$0.0005 estimated, demo checks ~$0.002) / about $0.31 cumulative of $5.

**Open issues**
- Gold labels still all `llm_assisted`, unreviewed. Over-refusals: q043 (test), q034/q039/q040/q057 (dev), mostly gate or no_answer on cross-lingual or mixed-script questions.
- A cross-lingual question about minors' minimum age was refused by the gate (top score under tau) even though the English page was retrieved: tau may hurt AR->EN questions. Worth checking in phase 11/13.
- tau rests on only 6 unanswerable dev questions. Test multi-turn n=3 is tiny.
- Correctness is about 53%: answers often omit key facts (e.g. q022 omits the flight ticket). No fix planned here.
- TDRA permission pending; phases 15-16 gated.

**Notes for next phase**
- Index version `2026-11-11-v2`, embeddings local only. Stored answer details for dev and test (`*_answers_rewrite_*`) are in `eval/results/details/`; phase 11 grades these.
- The multi-turn demo example only works because the follow-up is rewritten; q023's follow-up ("and may they work at night?") fails, so avoid it.
- CPU rerank latency still ~12 s (phase 16).

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
