# Handoff

Read at the start of every phase. At the end of each phase, **replace** the "Latest handoff" section with the new one (template below) and add one line to "History". Keep this file short. Details belong in commits and `docs/results.md`.

## Latest handoff

**Phase:** 11-judge-validation
**Date:** 2026-11-13
**Status:** done (with a caveat: the grades are Claude's, not the owner's, at the owner's request)

**Done**
- `judge.export_blind`, `judge.agreement`, `judge.kappa`, `judge.record_agreement`; CLI `judge-export`, `judge-agreement`. 107 tests pass (not slow), ruff clean.
- 45 items (dev 30 + test 15) graded blind (judge verdicts and `key.json` not read) by **Claude Sonnet 5.5**, not a human. `grades.csv` rows carry note `claude-graded`; results rows are labelled `claude-v1`.
- Judge target met on every criterion, so no `JUDGE_SYSTEM` revision and no re-judge.

**Deviations from plan**
- The phase file requires the owner's grades. The owner asked Claude to grade instead. So the numbers measure gpt-6.1-terra vs Claude agreement, **not human agreement**. The README must not say "agrees with human grades". Re-grade by hand (~2.5 h) and run `judge-agreement --label human-v1 --record` to get the real number; the grading sheet stays in `eval/grading/` (local).

**Metrics** (claude-v1; judge vs Claude grades)

| criterion | n | agreement | κ | judge pass / grader pass |
|---|---|---|---|---|
| faithfulness | 45 | 100% | undefined (all pass) | 45 / 45 |
| correctness | 45 | 98% | 0.96 | 24 / 25 (1 judge fail, grader pass: test) |
| citation_accuracy | 45 | 100% | 1.00 | 44 / 44 |

Test only: correctness 93% (κ 0.86), the others 100%. Faithfulness κ is undefined because every answer passed, so it says nothing about whether the judge can catch an unfaithful answer.

**OpenAI spend:** $0 this phase / about $0.31 cumulative of $5.

**Open issues**
- Grades are not human (see above). Same model family could share blind spots with the judge.
- The ~53% correctness is real, not judge strictness: the grader also failed 20/45, nearly always because the answer omits a key fact (e.g. q022-style omissions), which matches the strict rubric.
- Faithfulness and citation accuracy have almost no failures, so their agreement is weakly informative.
- Gold labels still `llm_assisted`; TDRA permission pending.

**Notes for next phase**
- Phase 12 needs Docker Desktop installed. Index version `2026-11-11-v2`, GATE_TAU 0.298 unchanged.

**Commit:** see PR #14

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
| 11 judge-validation | 2026-11-13 | done* | judge vs Claude-graded: correctness 98%, κ 0.96 (not human); $0 |
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
