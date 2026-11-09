# Phase 09: Reranker, pair collapse, and the refusal gate

**Size:** ~3.5 h · **Depends on:** phase 08 merged · **Cost:** ~$0.08 (one test answer eval; D64)

## Goal

A cross-encoder reranks the top-20 hybrid candidates, translations of the same page stop wasting context slots, and a data-chosen score threshold τ refuses obviously unanswerable questions without calling the LLM. All measured against phase 08.

## Decisions that apply

- Reranker (D25): `BAAI/bge-reranker-v2-m3` via `sentence_transformers.CrossEncoder`, `max_length = 512`, **sigmoid** scores in 0–1. It reranks `RERANK_TOP_N = 20` candidates. (The fallback to top-10 when HF p95 > 3 s is applied in phase 16 with real numbers.)
- **Pair collapse** (D31b): walk the reranked list in order; the first language seen for a `page_id` wins; later chunks of the same `page_id` in the **other** language are dropped. Same-language chunks of the same page are kept. Applied to the whole reranked list, so lower items move up to fill (backfill).
- `ranked = collapse(reranked)`, `final = ranked[:5]`, `top_score = reranked[0].score`.
- **Gate** (D26a): if `GATE_TAU` is set and `top_score < GATE_TAU` → refuse with `refusal_reason="gate"`, **no LLM call**; the answer is the localized refusal + up to 3 closest pages (same shape as the `no_answer` refusal).
- **Choosing τ** (D26a): on the **dev** split. Candidates are every distinct `top_score` (and +∞); predicted refuse = `top_score < τ`; positive class = "should refuse" (unanswerable). Pick the τ with max F1; ties → the smallest τ.
  - **Safety rule:** if the best F1 < 0.5, or that τ refuses more than 10% of dev's answerable questions, set `GATE_TAU = None` (gate off; `NO_ANSWER` remains) and record why.
  - Multi-turn questions are excluded from τ selection here (their last turn isn't rewritten until phase 10); phase 10 re-picks τ with them.

## Tasks

1. Add the `[09]` constants to `config.py` (`GATE_TAU = None` for now).
2. **`src/arengov/rerank.py`:** `@functools.cache _model()` → `CrossEncoder(RERANK_MODEL, max_length=RERANK_MAX_LENGTH, device="cuda" if available else "cpu")`. `rerank(query, chunks, idxs)` builds pairs `(query, chunks[i]["text"])`, calls `model.predict(pairs, batch_size=16, activation_fn=torch.nn.Sigmoid())`, and returns `[(idx, float(score))]` sorted desc. The keyword is `activation_fn` in sentence-transformers ≥ 3; check the installed version and use its name.
3. **`retrieve.collapse_pairs(ranked, chunks)`** as specified above.
4. **`pipeline.retrieve`:**
   - with `use_rerank`: `reranked = rerank(query, chunks, [i for i, _ in candidates[:RERANK_TOP_N]])`, `top_score = reranked[0][1]`;
   - else `reranked = candidates`, `top_score = None`;
   - then `ranked = collapse_pairs(reranked, chunks)` and `final = ranked[:TOP_K_CONTEXT]`;
   - add `"reranked": reranked` to `stages`.
5. **`pipeline.answer`:** apply the gate before `generate`. Build the refusal in one helper shared by the gate and `no_answer`.
6. **`pick-tau` CLI** (in `eval_retrieval.py` as `pick_tau(split="dev")`):
   - collect `(top_score, should_refuse)` for dev questions except `multi_turn`;
   - print a sorted table of scores with labels, then the best τ with precision, recall, F1, and the number of answerable questions it would refuse;
   - apply the safety rule and print the recommended `GATE_TAU`.
   Then edit `config.GATE_TAU` to that value (rounded to 3 decimals).
7. **Rerank latency:** time `rerank` of 20 real candidates on **CPU** (force `device="cpu"` in a one-off script or env override) over 10 queries; report p50/p95 in HANDOFF. It predicts HF Spaces latency for phase 16.
8. **Tests:**
   - `collapse_pairs`: [p1-en, p1-ar, p2-ar, p1-en(2nd chunk), p3-en] → [p1-en, p2-ar, p1-en(2nd), p3-en].
   - the gate: `retrieve` faked with `top_score` below τ → `refused`, `refusal_reason == "gate"`, `complete` never called; above τ → `generate` called.
   - the τ picker on a synthetic score list with a known best τ, plus the safety-rule fallback.
   - `@pytest.mark.slow`: `rerank` scores a relevant passage above an irrelevant one for an AR query.
9. **Eval runs** (`--record`):
   - `eval-retrieval --split test --label hybrid-rerank`
   - `eval-retrieval --split test --cross-lingual --label hybrid-rerank-xling`
   - `eval-retrieval --split dev --label hybrid-rerank`
   - `eval-answers --split test --label rerank-gate` (test only, D64; defaults: `--backend openai`, terra judge)
   (The no-rerank ablation is the phase 08 `hybrid` row. Any manual checks of the gate with `ask` use `LLM_BACKEND=ollama`; the gate itself makes no LLM call.)
10. **Ratchet thresholds** with the new test summaries; `check-thresholds` passes. If `refusal_correct` went up but a retrieval metric dropped, report it honestly in HANDOFF.

## Files

Create: `src/arengov/rerank.py`, `tests/test_rerank.py`. Change: `retrieve.py`, `pipeline.py`, `eval_retrieval.py`, `config.py`, `__main__.py`, `eval/thresholds.json`, `docs/results.md`, `docs/HANDOFF.md`.

## Acceptance criteria

- `uv run pytest` (including slow) passes; ruff clean.
- `GATE_TAU` is set from `pick-tau` (or `None`, with the reason in HANDOFF).
- 4 new rows in `docs/results.md`; `check-thresholds` passes.

## Out of scope

Follow-up rewriting is phase 10, so τ is re-picked there including multi-turn questions. The rerank top-N fallback is applied in phase 16 with measured HF latency.

## What you should understand after this phase

- **Bi-encoder vs cross-encoder:** embeddings encode query and passage separately (fast, approximate); a cross-encoder reads them together (slow, precise). Hence retrieve wide with the cheap model, rerank narrow with the expensive one.
- **Why recall@20 bounds recall@5 after reranking:** a reranker can only promote what retrieval found.
- **Redundancy in context:** two translations of one page are one piece of evidence. Collapse buys diversity in the 5 slots.
- **Threshold selection from data:** precision/recall/F1 for "should refuse", why F1, why the safety rule. A gate that refuses good questions is worse than no gate.
- **Two refusal layers:** the gate is cheap and catches the obvious; `NO_ANSWER` catches subtle near-misses that need reading.

## Handoff checklist

- [ ] Acceptance criteria pass.
- [ ] HANDOFF: τ (or None + why) with its dev F1, CPU rerank p50/p95, a before/after table vs phase 08, the new thresholds.
- [ ] Committed on `phase-09-rerank-gate`, pushed, PR open.
- [ ] Told the owner: merge when green, `/clear`, next is phase 10.
