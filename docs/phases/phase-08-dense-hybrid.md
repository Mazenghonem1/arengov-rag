# Phase 08: Dense embeddings, hybrid retrieval with RRF

**Size:** ~3.5 h (includes ~15–30 min of embedding on the GPU) · **Depends on:** phase 07 merged · **Cost:** ~$0.30

## Goal

Chunks get bge-m3 embeddings, retrieval runs BM25 and dense search in parallel and fuses them with Reciprocal Rank Fusion, `"hybrid"` becomes the default mode, and the ablation rows (dense-only, hybrid, cross-lingual) are recorded against the BM25 baseline.

## Decisions that apply

- Embeddings (D22): `BAAI/bge-m3`, dense only, via `sentence-transformers`, L2-normalized, float32, no query prefix. `max_seq_length = 512`. Built locally once (GPU here) and shipped as `embeddings.npy` (D23). Embeddings get the raw chunk text, never the Arabic-normalized text (D16).
- No vector DB: exact cosine = dot product of normalized vectors in NumPy (D23).
- Fusion (D24): BM25 top-50 + dense top-50 → RRF with `k = 60` (`score = Σ 1/(k + rank)`, rank 1-based; ties by idx asc) → top-20 `candidates`.
- Every rebuild bumps the index version (PLAN.md § Paths): this phase builds `<snapshot>-v2` with embeddings and switches `eval/index_version.txt` to it.
- torch comes from the PyTorch wheel index: CUDA on Windows (this dev box, RTX 3060 Ti), CPU on Linux (Docker, CI, HF Spaces).

## Tasks

1. **torch setup.** Run `nvidia-smi` and read the "CUDA Version" in its header. Choose the newest PyTorch CUDA wheel index `cuXXX` whose version is ≤ that (try `cu128` first, then `cu126`). Add to `pyproject.toml`:
   ```toml
   [[tool.uv.index]]
   name = "pytorch-cuda"
   url = "https://download.pytorch.org/whl/cu128"   # or the chosen cuXXX
   explicit = true

   [[tool.uv.index]]
   name = "pytorch-cpu"
   url = "https://download.pytorch.org/whl/cpu"
   explicit = true

   [tool.uv.sources]
   torch = [
     { index = "pytorch-cuda", marker = "sys_platform == 'win32'" },
     { index = "pytorch-cpu", marker = "sys_platform == 'linux'" },
   ]
   ```
   Then `uv add torch sentence-transformers`. Check: `uv run python -c "import torch; print(torch.cuda.is_available())"` prints `True`. If it prints `False`, stop and ask the owner (driver issue). CPU embedding would take hours.
2. Add the `[08]` constants to `config.py`.
3. **`src/arengov/embed.py`:** `@functools.cache _model()` → `SentenceTransformer(EMBED_MODEL, device="cuda" if torch.cuda.is_available() else "cpu")`, with `max_seq_length = 512`. `embed_texts(texts, batch_size=16)` → `model.encode(texts, batch_size=batch_size, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=len(texts) > 100).astype(np.float32)`. `embed_query(text)` → `embed_texts([text])[0]`.
4. **`src/arengov/retrieve.py`:**
   - `dense_search(qvec, embeddings, top_n, mask=None)`: `scores = embeddings @ qvec`; masked rows set to `-inf`; top_n via `np.argpartition` then sort desc (ties by idx); returns `[(idx, float(score))]`.
   - `rrf(rankings, k=RRF_K)`: rankings is a list of idx lists; returns `[(idx, fused_score)]` sorted desc, ties by idx asc.
5. **`index.py`:**
   - `build_index(snapshot_id, index_version, embed=False)`: when `embed`, embed all chunk texts, save `embeddings.npy`, and set `meta.embed_model`. Print the device and the elapsed time.
   - `Index.embeddings` is loaded with `np.load` when the file exists, else `None`.
   - Assert `embeddings.shape == (len(chunks), 1024)`.
6. **`pipeline.retrieve`:** `mode` ∈ `"bm25" | "dense" | "hybrid"`, default **`"hybrid"`**.
   - bm25 = BM25 top `BM25_TOP_N`;
   - dense = `dense_search(embed_query(query), index.embeddings, DENSE_TOP_N, mask)`;
   - candidates: bm25 mode → bm25[:FUSED_TOP_N], dense mode → dense[:FUSED_TOP_N], hybrid → `rrf([ids of bm25, ids of dense])[:FUSED_TOP_N]`;
   - `ranked = candidates` (no reranker yet), `final = ranked[:TOP_K_CONTEXT]`;
   - `stages = {"bm25": bm25, "dense": dense}`;
   - only compute what the mode needs.
   Update the PLAN.md contract note: the default is now `"hybrid"`.
7. **CLI:** `build-index … [--embed]`; `search` and `eval-retrieval` accept `--mode bm25|dense|hybrid`.
8. **Tests:**
   - `tests/test_retrieve.py`: `rrf` on two toy rankings with the expected fused scores written as explicit fractions (e.g. `1/61 + 1/62`); `dense_search` on a tiny 4×3 matrix with and without a mask.
   - `@pytest.mark.slow` `tests/test_embed.py`: an EN sentence and its AR translation have higher cosine similarity than the EN sentence and an unrelated AR sentence; the output is normalized (norm ≈ 1).
9. **Build** `build-index --snapshot <id> --version <id>-v2 --embed` (writes `eval/index_version.txt`). The chunks must be identical to v1: compare line counts and `chunk_id`s.
10. **Eval runs** (all `--record`, test split unless stated):
    - `eval-retrieval --mode dense --label dense`
    - `eval-retrieval --mode hybrid --label hybrid`
    - `eval-retrieval --mode dense --cross-lingual --label dense-xling`
    - `eval-retrieval --mode hybrid --cross-lingual --label hybrid-xling`
    - `eval-retrieval --split dev --mode hybrid --label hybrid`
    - `eval-answers --split test --label hybrid`
11. **Ratchet thresholds:** `set-thresholds <hybrid test retrieval summary> <hybrid test answers summary>`; `check-thresholds` passes.
12. In HANDOFF, write the comparison: BM25 vs dense vs hybrid (recall@5, MRR@10, xling recall@5) and one sentence on what it shows.

## Files

Create: `src/arengov/embed.py`, `src/arengov/retrieve.py`, `tests/test_retrieve.py`, `tests/test_embed.py`. Change: `pyproject.toml`, `uv.lock`, `index.py`, `pipeline.py`, `config.py`, `__main__.py`, `eval/index_version.txt`, `eval/thresholds.json`, `docs/results.md`, `docs/PLAN.md`, `docs/HANDOFF.md`.

## Acceptance criteria

- `uv run pytest` (including slow) passes; ruff clean.
- `data/index/<id>-v2/embeddings.npy` has shape `(n_chunks, 1024)`; `eval/index_version.txt` = `<id>-v2`.
- 6 new rows in `docs/results.md`; `check-thresholds` passes on the hybrid test summaries.
- Dense cross-lingual recall@5 is clearly above BM25's near-zero. If not, investigate before finishing.

## Out of scope

The reranker, pair collapse and gate are phase 09. Embedding uses only the raw text (no normalization, no instruction prefix). FAISS or a vector DB isn't needed at this scale (D23); the README explains why in phase 17.

## What you should understand after this phase

- **Dense retrieval:** a shared multilingual vector space where a question and its answer land close together **across languages**. That's why cross-lingual recall jumps.
- **Cosine similarity = dot product** of normalized vectors; brute force over ~5k × 1024 floats takes milliseconds.
- **Sparse vs dense strengths:** BM25 nails exact terms (fees, form names, numbers), dense nails paraphrase and other languages. Hybrid gets both.
- **RRF:** fuses rankings without comparing incompatible scores; `k` dampens the weight of top ranks.
- **Build artifacts and versions:** why a new embedding means a new index version.

## Handoff checklist

- [ ] Acceptance criteria pass.
- [ ] HANDOFF: the torch index used, embedding time, the BM25/dense/hybrid comparison, the new thresholds.
- [ ] Committed on `phase-08-dense-hybrid`, pushed, PR open.
- [ ] Told the owner: merge when green, `/clear`, next is phase 09.
