# Phase 03: Arabic-aware text processing and hand-written BM25

**Size:** ~3 h · **Depends on:** phase 02 merged; `eval/index_version.txt` points to a built index

## Goal

`uv run python -m arengov search "<query>"` returns the top chunks by BM25 over both languages, using an Arabic-aware tokenizer you wrote, a BM25 you wrote, and language detection.

## Prerequisites

- Index `<id>-v1` from phase 02.

## Decisions that apply

- **Language detection (D15):** count letters (`str.isalpha()`). Arabic letters = characters in U+0600–U+06FF, U+0750–U+077F, U+08A0–U+08FF, U+FB50–U+FDFF, U+FE70–U+FEFF that are `isalpha()`. Arabic share ≥ 0.5 → `"ar"`, else `"en"`. No letters → `"en"`.
- **Arabic normalization (D16)**, BM25 only, never for embeddings:
  - strip diacritics U+064B–U+0652 and U+0670, and tatweel U+0640
  - أ إ آ ٱ → ا
  - ى → ي
  - ة → ه
  - ی → ي, ک → ك
  - ٠–٩ (U+0660–U+0669) and ۰–۹ (U+06F0–U+06F9) → 0–9
  - leave ؤ ئ unchanged
- **Tokenizer (D17):**
  1. Always strip diacritics and tatweel first (tokenization hygiene; otherwise `\w` splits words at diacritics).
  2. Lowercase.
  3. Split with `re.findall(r"[^\W_]+", text)`.
  4. Per token: if it contains any Arabic-range character → Arabic path: if `normalize`, apply `normalize_ar` and then the Snowball **arabic** stemmer. Otherwise → English path: drop if in `EN_STOPWORDS`; if `normalize`, apply the Snowball **english** stemmer.
  5. With `normalize=False` (the ablation): no letter folding, no digit mapping, no stemming, but stopwords are still dropped.
  `EN_STOPWORDS` = `a an and are as at be by can do for from how i in is it my of on or the to what when where which who with you your`.
- **BM25 (D17):** Okapi, `k1 = 1.5`, `b = 0.75`. Query terms are **deduplicated**. For a document d and query term t:
  - `idf(t) = ln((N - df + 0.5) / (df + 0.5) + 1)`
  - `score += idf(t) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl))`
  - Here N = number of docs, df = docs containing t, tf = count of t in d, dl = token count of d, avgdl = mean dl.
  - One index over both languages (an Arabic query naturally only matches Arabic tokens). `mask` (bool np array) restricts which docs may be returned.
- `pipeline.retrieve` is introduced here with `mode="bm25"` only (PLAN.md § Modules).

## Tasks

1. `uv add snowballstemmer`. Check `snowballstemmer.stemmer("arabic")` works; it needs snowballstemmer ≥ 2.1.
2. Add the `[03]` constants to `config.py`.
3. **`src/arengov/text_ar.py`:** `is_arabic_char(c)`, `detect_lang(text)`, `normalize_ar(text)`, `tokenize(text, normalize=True)`, with module-level cached stemmers and `EN_STOPWORDS`. Implement `normalize_ar` with one `str.maketrans` table plus a regex for diacritics.
4. **`src/arengov/bm25.py`:** `class BM25`:
   - `__init__(docs_tokens, k1=BM25_K1, b=BM25_B)` builds `doc_len` (np array), `avgdl`, `N`, and an inverted index `term -> list[(doc_idx, tf)]`, plus `idf` per term.
   - `search(query_tokens, top_n, mask=None)` accumulates scores in an np.zeros(N) array over the postings of each unique query term. Docs with score 0 or masked-out docs are excluded. Return `[(idx, score)]` sorted by score desc, ties by idx asc, length ≤ top_n.
5. **`index.py`:** `load_index` builds `Index.bm25 = BM25([tokenize(c["text"]) for c in chunks])`. `Index.bm25_nonorm` is built lazily on first access (use `functools.cached_property`, or build in a helper) with `tokenize(..., normalize=False)`. Cache `load_index` per version (`functools.cache`).
6. **`src/arengov/pipeline.py`:** `retrieve(query, *, lang_filter=None, mode="bm25", use_rerank=True, use_norm=True)`:
   - mask = `index.langs == lang_filter` if `lang_filter`, else None.
   - bm25 = (`index.bm25` if `use_norm` else `bm25_nonorm`).search(`tokenize(query, normalize=use_norm)`, `BM25_TOP_N`, mask).
   - Return the PLAN.md dict: `candidates = bm25[:20]`, `ranked = bm25`, `final = ranked[:TOP_K_CONTEXT]`, `top_score = None`, `stages = {"bm25": bm25}`.
   - `mode` values other than `"bm25"` raise `ValueError` until phase 08. `use_rerank` is ignored until phase 09.
7. **CLI:** `search "QUERY" [--lang-filter ar|en] [--no-norm] [-k 10]` prints rank, score (3 decimals), chunk_id, heading_path.
8. **Tests:**
   - `tests/test_text_ar.py`: one parametrized case per normalization rule (each letter mapping, diacritics, tatweel, both digit sets, ؤ/ئ unchanged). `detect_lang` on pure AR, pure EN, `"how to renew الإقامة"` → `"en"`, `"ما هي شروط الإقامة الذهبية golden visa"` → `"ar"`, digits only → `"en"`. `tokenize`: Arabic with diacritics and the definite article gives stemmed tokens; EN plural and singular stem to the same token; stopwords removed; with `normalize=False`, أ and ا stay different tokens.
   - `tests/test_bm25.py`: a toy corpus of 3 docs (pre-tokenized lists) with a 2-term query, where the **expected score for one doc is written out as explicit arithmetic** in the test (idf and tf parts computed literally from the formula above, not by calling the implementation). Also: ranking order, mask excludes docs, zero-score docs absent, duplicate query terms counted once.
9. **Try it on real data:** run 3 EN and 3 AR queries the owner suggests (or defaults like "golden visa requirements", "تجديد الهوية الإماراتية", "trade license types"). Show the results, and run one query with `--no-norm` to see the difference.

## Files

Create: `src/arengov/text_ar.py`, `src/arengov/bm25.py`, `src/arengov/pipeline.py`, `tests/test_text_ar.py`, `tests/test_bm25.py`. Change: `index.py`, `config.py`, `__main__.py`, `pyproject.toml`, `uv.lock`, `docs/HANDOFF.md`.

## Acceptance criteria

- `uv run pytest -m "not slow"` passes, including the hand-computed BM25 score; ruff clean.
- `search` returns relevant-looking chunks for the 6 sample queries (owner agrees), and `--lang-filter` / `--no-norm` work.
- Building BM25 over the full index takes <30 s (print the timing once).

## Out of scope

BM25 is in-memory and rebuilt at load; no persistence. Query translation or expansion across languages is stretch (D19). This phase retrieves only; answering is phase 04.

## What you should understand after this phase

- **BM25 term by term:** what IDF rewards (rare words), what tf saturation (`k1`) does, why length normalization (`b`) stops long chunks from winning by size. You should be able to compute a score by hand.
- **Inverted index:** why scoring only the postings of query terms is fast.
- **Arabic orthographic variation:** hamza forms on alef, alef maqsura vs ya, ta marbuta vs ha, optional diacritics, two sets of digits. Why folding them raises recall, and what it might cost in precision.
- **Stemming vs lemmatization**, and why a light stemmer is enough for retrieval.
- **Why BM25 alone can't do cross-lingual retrieval:** Arabic and English tokens never overlap. The dense model in phase 08 fixes this.

## Handoff checklist

- [ ] Acceptance criteria pass.
- [ ] HANDOFF: the sample queries with the top-3 heading_paths each; BM25 build time.
- [ ] Committed on `phase-03-bm25`, pushed, PR open.
- [ ] Told the owner: merge when green, `/clear`, next is phase 04.
