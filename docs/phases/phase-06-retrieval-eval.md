# Phase 06: Retrieval evaluation and the BM25 baseline

**Size:** ~3 h · **Depends on:** phase 05 merged (`eval/questions.jsonl` valid, 60 questions)

## Goal

`uv run python -m arengov eval-retrieval` computes recall@5, recall@20 and MRR@10 per language and type, in normal and cross-lingual mode, writes a summary JSON, and appends a row to `docs/results.md`. The BM25 baseline rows are recorded.

## Decisions that apply

- Metrics (D36): on **answerable** questions only (types `single`, `multi_turn`, `mixed_script`). A hit = any gold `page_id` among the chunks' `page_id`s.
  - `recall@5`: hit in `final` (top-5).
  - `recall@20`: hit in the first 20 of `candidates`.
  - `mrr@10`: 1/rank of the first chunk in `ranked[:10]` whose page_id is gold, else 0.
- **Cross-lingual mode** (D31a): retrieve with `lang_filter` = the opposite of the question's `lang`. This is the honest cross-lingual number.
- Multi-turn questions: the query is the **last turn as-is** until phase 10 adds rewriting (D58).
- Results files and `docs/results.md`: PLAN.md § Paths and § Metric keys (D57). Per-question details go to gitignored `eval/results/details/`.
- Ablations reported later: BM25 / dense / hybrid / +rerank / normalization off (D36).

## Tasks

1. **`src/arengov/eval_retrieval.py`:**
   - Pure functions `hit_at(page_ids, gold, k) -> bool` and `rr_at(page_ids, gold, k) -> float`.
   - `run(split, *, mode="bm25", use_rerank=True, use_norm=True, cross_lingual=False, label, record=False)`:
     - Load questions (`split` ∈ dev/test/all); keep answerable ones.
     - For each: query = `turns[-1]`; `lang_filter` = (`"en"` if `lang == "ar"` else `"ar"`) when `cross_lingual`, else None. Call `pipeline.retrieve(query, lang_filter=…, mode=mode, use_rerank=use_rerank, use_norm=use_norm)`. Map indices to `page_id`s and compute the three metrics.
     - Summary dict: `{kind: "retrieval", label, split, index_version, git_sha, timestamp, config: {mode, use_rerank, use_norm, cross_lingual}, n, metrics: {recall@5, recall@20, mrr@10}, by_lang: {ar: {...}, en: {...}}, by_type: {...}}`.
     - Write `eval/results/<YYYYMMDD-HHMM>_retrieval_<label>_<split>.json` and `eval/results/details/<same stem>.jsonl` (id, lang, type, query, top-5 page_ids, hit flags, rr).
     - Print a compact table: overall, by lang, by type.
     - When `record`: append a row to `docs/results.md`.
     - Return the summary.
   - Also accept an `--out PATH` CLI option that writes a copy of the summary there (used by CI in phase 15).
2. **`docs/results.md`:** create it with a short intro and one table:
   ```
   | date | label | split | index | mode | xling | rerank | norm | recall@5 | recall@20 | mrr@10 | refusal | lang | cite valid | faithful | correct | cite acc | p95 ms | $/q |
   ```
   Retrieval rows fill the retrieval columns and put `—` in the answer columns. Rates are shown as percentages with no decimals.
3. **CLI:** `eval-retrieval --split dev|test|all --label NAME [--mode bm25] [--cross-lingual] [--no-norm] [--no-rerank] [--record] [--out PATH]`.
4. **Tests** (`tests/test_eval_retrieval.py`): `hit_at` / `rr_at` on hand-made lists (gold at rank 1, at rank 7 with k=5 and k=10, absent, duplicate pages); `run` on 3 synthetic questions with `pipeline.retrieve` and the index monkeypatched, checking the metric values and that unanswerable questions are excluded.
5. **Baseline runs** (all with `--record`):
   - `--split dev --label bm25-baseline`
   - `--split test --label bm25-baseline`
   - `--split test --label bm25-xling --cross-lingual`
   - `--split test --label bm25-nonorm --no-norm`
6. Look at the dev details file: list the 5 worst misses (query + top-3 page titles vs gold) and give the owner a one-line guess at each cause (vocabulary mismatch, wrong language, chunking). Put that in HANDOFF; it motivates phase 08.

## Files

Create: `src/arengov/eval_retrieval.py`, `tests/test_eval_retrieval.py`, `docs/results.md`, `eval/results/*.json` (4 summaries). Change: `__main__.py`, `docs/HANDOFF.md`.

## Acceptance criteria

- `uv run pytest -m "not slow"` passes; ruff clean.
- `docs/results.md` has the 4 baseline rows; the 4 summary JSONs are committed; `eval/results/details/` is not committed.
- The cross-lingual recall for BM25 is near 0, as BM25 can't match across scripts. If it isn't, investigate (likely a mask bug) before finishing.

## Out of scope

Answer quality and the LLM judge are phase 07. Thresholds/CI gates come after the answer baseline (phase 07 writes `thresholds.json`). Retrieval improvements are phases 08–10; record the baseline as it is.

## What you should understand after this phase

- **recall@k vs MRR:** recall asks "is the right page anywhere in the top k?", MRR asks "how high is it?". The generator sees only the top-5, so recall@5 is the number that matters most, and recall@20 shows the ceiling a reranker could reach.
- **Why page-level hits:** several chunks of the same page are equivalent evidence.
- **Cross-lingual mode as an experiment design:** removing the same-language copy forces the system to bridge languages, so the number measures exactly one capability.
- **Ablation:** change one thing, keep everything else fixed, and attribute the difference.
- **Error analysis:** read the misses; averages hide why.

## Handoff checklist

- [ ] Acceptance criteria pass.
- [ ] HANDOFF: the 4 baseline rows; the 5 worst misses with cause guesses.
- [ ] Committed on `phase-06-retrieval-eval`, pushed, PR open.
- [ ] Told the owner: merge when green, `/clear`, next is phase 07.
