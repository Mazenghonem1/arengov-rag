# Handoff

Read at the start of every phase. At the end of each phase, **replace** the "Latest handoff" section with the new one (template below) and add one line to "History". Keep this file short. Details belong in commits and `docs/results.md`.

## Latest handoff

**Phase:** 03-bm25
**Date:** 2026-11-11
**Status:** done

**Done**
- `text_ar.py` (`is_arabic_char`, `detect_lang`, `normalize_ar`, `tokenize`), `bm25.py` (`BM25`), `pipeline.retrieve` (`mode="bm25"` only), `Index.bm25` / `Index.bm25_nonorm` (lazy `cached_property`), `load_index` cached, CLI `search "Q" [--lang-filter] [--no-norm] [-k]`, `[03]` config constants.
- Tests: `test_text_ar.py` (every normalization rule, `detect_lang`, `tokenize`), `test_bm25.py` (hand-computed score, order, mask, zero-score, dedup).

**Deviations from plan**
- None. `snowballstemmer` 3.1.1 installed; the Arabic stemmer works.

**Metrics:** tests: 41 passed (1 deselected as slow), ruff clean. BM25 build over 868 chunks: **4.3 s** (limit 30 s).

Top-3 per sample query (heading_path; EN chunk ids are `en:<page_id>:<i>`):

| Query | Top 3 |
|---|---|
| golden visa requirements | Golden visa > Related digital services (types-of-visas, and a duplicate under residence-visas, same score); Golden visa > What is the Golden visa? |
| trade license types | Starting a business in a free zone > Key steps; Steps to start a business on the mainland > Registering the trade name; … > Applying for a trade licence |
| how to renew Emirates ID | Emirates ID > Renewing Emirates ID; > Related eServices; > Emirates ID within 24 hours |
| تجديد الهوية الإماراتية | بطاقة الهوية الإماراتية > تجديد بطاقة الهوية الإماراتية; > الخدمات الإلكترونية ذات الصلة; > ما هي بطاقة الهوية الإماراتية؟ |
| التأشيرة الذهبية | الإقامة الذهبية > ما هي الإقامة الذهبية؟; > الخدمات الرقمية ذات الصلة; أحكام عامة عن تأشيرة الإقامة > مدة سريان تأشيرة الإقامة |
| رخصة تجارية | … > التقديم على رخصة تجارية; استعلم عن أسماء الرخص التجارية المسجلة وأنشطتها; التجارة الإلكترونية > تراخيص الأعمال … |

`--no-norm` on "تجديد الهوية الإماراتية": same top 2, but rank 3 becomes the "Emirates ID within 24 hours" chunk (exact-form match on "الهوية") instead of "ما هي بطاقة الهوية". `--lang-filter ar` with an English query returns nothing, as expected (no token overlap).

**OpenAI spend:** $0 / $0

**Open issues**
- "Related digital services" link-only chunks rank first for "golden visa" (the heading repeats the query terms; they are in the chunk text). Known from phase 02; revisit if phase 06 recall suffers.
- The same page can appear under two URLs (`types-of-visas/golden-visa` and `residence-visas/golden-visa`) with identical scores. Evaluate in phase 06 whether gold `page_id`s need both.
- The Snowball Arabic stemmer is uneven: "الاقامه" → "اقامه" but bare "اقامه" → "اقام". Acceptable for retrieval; note for the ablation write-up.
- TDRA: no written permission yet; phases 15-16 stay gated.

**Notes for next phase**
- Index version in use: `2026-11-11-v1`.
- `retrieve` raises `ValueError` for any mode other than `"bm25"`; `use_rerank` is ignored until phase 09.
- Phase 04 needs an `LLM_BACKEND=ollama` (qwen3:8b) setup for free testing.

**Commit:** see PR

## History

| Phase | Date | Result | Key metric |
|---|---|---|---|
| planning | 2026-11-09 | done | — |
| 00 setup | 2026-11-09 | done | CI green |
| 01 crawl | 2026-11-11 | done | 145 EN / 143 AR pages |
| 02 clean-chunk | 2026-11-11 | done | 868 chunks (419 EN / 449 AR), max 400 tokens |
| 03 bm25 | 2026-11-11 | done | BM25 build 4.3 s, 41 tests |

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
