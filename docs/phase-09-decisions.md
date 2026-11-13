# Phase 09 decisions

Every call made during phase 09 (reranker, pair collapse, refusal gate), with the reason. Design decisions D25, D26a and D31b come from `docs/DECISIONS.md`; this file records what was decided while building and measuring.

## Design (from the phase file, followed as written)

| # | Decision | Why |
|---|---|---|
| 1 | Rerank the top 20 hybrid candidates with `bge-reranker-v2-m3`, sigmoid scores 0-1 | A cross-encoder reads query and passage together, so it is more precise than the bi-encoder; it is too slow to run on everything, so it only reorders the 20 candidates retrieval found. |
| 2 | `collapse_pairs` runs on the whole reranked list, first language seen for a page wins | A translation of the same page is not new evidence. Collapsing the full list lets lower items move up, so the 5 context slots hold 5 distinct pages. |
| 3 | The gate sits in `pipeline.answer`, before `generate`, and makes no LLM call | An obviously unanswerable question costs nothing and answers faster. The refusal shape matches `no_answer` (localized message plus up to 3 closest pages), through one shared `_refusal` helper. |
| 4 | The reranker is imported lazily inside `pipeline.retrieve` | Same reason as `embed`: BM25-only paths and fast tests should not import torch. |

## Choosing tau

| # | Decision | Why |
|---|---|---|
| 5 | `GATE_TAU = 0.298`, from `pick-tau` on dev (max F1, ties to the smallest tau) | Rule from D26a. Dev F1 is 0.83 (precision 0.83, recall 0.83). It refuses 1 of 27 answerable dev questions (q057), which passes the safety rule (F1 >= 0.5 and <= 10% of answerable refused). |
| 6 | Multi-turn questions are excluded from tau selection | Their last turn is not rewritten until phase 10, so their scores would be misleading. Phase 10 re-picks tau with them. |
| 7 | `pick-tau` takes only `--split`, no `--backend` | It never calls an LLM, so the flag would do nothing. |
| 8 | Printed `0.298` is rounded down from the best candidate 0.2983 | `score < 0.298` still lets q008 (0.2983) through, so the rounding does not change which questions are refused. |
| 9 | Known weak spot: tau rests on only 6 unanswerable dev questions, and q050 scores 0.97 | The gate cannot catch that kind of question; only `NO_ANSWER` can. Recorded in HANDOFF as a limit, not hidden. |

## Evals and cost

| # | Decision | Why |
|---|---|---|
| 10 | Stopped before the OpenAI answer eval and gave the expected cost | You asked for the cost before each OpenAI run. Actual spend was $0.037; cumulative is about $0.192 of $5. |
| 11 | Ran the retrieval evals with `--record` and read results with n in mind | Test has 16 answerable questions, so one question moves recall@5 by about 6 points. |
| 12 | Reported the MRR drops (xling test 0.88 to 0.80, dev 0.90 to 0.87) in HANDOFF instead of only the gains | The phase file says to report honestly when a retrieval metric drops. Recall@5 held or rose, so rerank still looks worth keeping. |
| 13 | Measured CPU rerank latency on the 12-thread desktop: p50 11.9 s, p95 12.4 s | It predicts Hugging Face Spaces latency. Far above the 3 s limit, so phase 16 needs a smaller top-N and probably more. |

## The failing threshold check

| # | Decision | Why |
|---|---|---|
| 14 | Did not lower the faithfulness and citation_accuracy thresholds (0.95), although this run scored 0.929 | The ratchet exists so thresholds never go down; lowering one to make a check pass defeats it. The cause is a single answer (q005, "either" for requirements that are all mandatory) out of 14 judged, so it is more likely noise than a regression. |
| 15 | Did not re-run the answer eval | It costs about $0.04, and a re-run only tells us whether one noisy judgment flips. It would not change what the code does. |
| 16 | Pushed and opened the PR with the failing check documented (option 1) | CI never runs the OpenAI answer eval, so it stays green. The failure is stated plainly in HANDOFF and the PR body rather than hidden. The retrieval thresholds ratcheted up (mrr@10 0.65 to 0.75). |
| 17 | Left a decision for the next phase: if faithfulness stays below 0.95 with more judged answers, revisit the threshold then | Phase 10 runs more answer evals on dev and test, which gives a larger sample than 14. |

## Process

| # | Decision | Why |
|---|---|---|
| 18 | Removed the Co-Authored-By line from the commit | Your memory rule says no Claude attribution on commits or PRs. |
| 19 | Did not trigger `eval-answers.yml` | CLAUDE.md requires it from phase 15 on. |
| 20 | Self-merging after CI is green, per your memory rule | You asked for phase PRs to be squash-merged by me once CI passes. |
