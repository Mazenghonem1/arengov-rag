# Plan

18 phases, ~66 h total, ~7 weeks at 9–10 h/week. Every phase ends tested and committed. **[YOU]** = owner-only work. Hours are the owner's time (supervising Claude + own work).

The order is baseline first (D51): a BM25-only pipeline gets an eval set and a measured baseline **before** dense retrieval, reranking and rewriting are added, so each later phase is measured against it.

## Phases

| # | Phase file | What it delivers | Hours | Cum. |
|---|---|---|---|---|
| 00 | `phase-00-setup.md` | uv project, CLI skeleton, test CI job, GitHub repo, TDRA email draft | 2 | 2 |
| 01 | `phase-01-crawl.md` | Polite crawler, dated snapshot + manifest, `diff` | 3 | 5 |
| 02 | `phase-02-clean-chunk.md` | HTML cleaning, heading-aware chunks, `build-index` (chunks only) | 3 | 8 |
| 03 | `phase-03-bm25.md` | Arabic normalization, tokenizer, language detection, hand-written BM25, `search` | 3 | 11 |
| 04 | `phase-04-generate.md` | LLM client (OpenAI + Ollama), cited answers, `NO_ANSWER` refusal, `ask` → **minimal pipeline** | 4 | 15 |
| 05 | `phase-05-eval-set.md` | Part A: eval-set tooling. **[YOU]** write 60 questions. Part B: validate + split | 9 | 24 |
| 06 | `phase-06-retrieval-eval.md` | Retrieval metrics, cross-lingual mode, results log, **BM25 baseline** | 3 | 27 |
| 07 | `phase-07-answer-eval.md` | Deterministic checks, LLM judge, **answer baseline**, CI thresholds file | 4 | 31 |
| 08 | `phase-08-dense-hybrid.md` | bge-m3 embeddings (GPU), dense search, RRF, ablation rows | 3.5 | 34.5 |
| 09 | `phase-09-rerank-gate.md` | Reranker, pair collapse, refusal gate τ from data | 3.5 | 38 |
| 10 | `phase-10-multiturn.md` | Query rewriting for follow-ups, demo examples chosen | 2.5 | 40.5 |
| 11 | `phase-11-judge-validation.md` | Part A: blind-grading CSV. **[YOU]** grade. Part B: agreement + κ | 4.5 | 45 |
| 12 | `phase-12-tracing.md` | Phoenix in Compose, spans per stage, PII scrubber | 3 | 48 |
| 13 | `phase-13-api-ui.md` | FastAPI, static bilingual UI, feedback, rate limits, disclaimer | 4.5 | 52.5 |
| 14 | `phase-14-docker-ops.md` | App Dockerfile + Compose, ops report, bad-feedback export | 3 | 55.5 |
| 15 | `phase-15-ci-gates.md` | Index on private HF dataset, retrieval eval gate on PRs, manual answer eval gate | 3 | 58.5 |
| 16 | `phase-16-deploy.md` | HF Spaces app + Phoenix Space + Neon, live smoke test | 4 | 62.5 |
| 17 | `phase-17-launch.md` | Qwen comparison row, README, Mermaid, results, **[YOU]** GIF | 4 | 66.5 |

Rough weeks: W1 = 00–02, W2 = 03–05A, W3 = 05 [YOU] + 05B–06, W4 = 07–09, W5 = 10–12, W6 = 13–15, W7 = 16–17.

**If time runs out**, cut from the end of this list: 17's Qwen row → 11 (report judge unvalidated, labelled as such) → 16's Phoenix Space (keep Phoenix local + GIF). Every phase up to 15 leaves a complete, measured system.

### Stretch backlog (D4, D19, D42): only after phase 17
- `judge_sampled.py`: weekly scheduled online judge on 20 sampled traces.
- Automated feedback → eval-case export.
- Custom dashboard page.
- Bilingual query expansion for BM25 (rewriter emits AR+EN queries), measured as an ablation.

---

## Architecture contracts

The single source of truth for interfaces. Phase files build against these. A phase that must change a contract updates this section in the same commit and notes it in HANDOFF.

### Data flow

```
crawl → data/snapshots/<snapshot_id>/{raw/*.html, manifest.jsonl}
build-index → clean → chunk → [embed] → data/index/<index_version>/{chunks.jsonl, embeddings.npy, meta.json}
ask: messages → [rewrite] → retrieve(bm25 + dense → RRF → rerank → collapse) → gate → generate → answer + citations
```

### Paths

| Path | Content | In git? |
|---|---|---|
| `data/snapshots/<snapshot_id>/raw/<sha1(url)>.html` | raw HTML | no |
| `data/snapshots/<snapshot_id>/manifest.jsonl` | one line per fetched page | no |
| `data/snapshots/<snapshot_id>/crawl.log` | one line per request | no |
| `data/index/<index_version>/chunks.jsonl` | chunk records | no |
| `data/index/<index_version>/embeddings.npy` | float32 `[n_chunks, 1024]`, L2-normalized, row i = chunk line i (phase 08+) | no |
| `data/index/<index_version>/meta.json` | `{index_version, snapshot_id, embed_model, n_chunks, created_at, git_sha}` | no |
| `eval/index_version.txt` | the index version everything uses, e.g. `2026-11-16-v1` | yes |
| `eval/questions.jsonl` | eval set | yes |
| `eval/thresholds.json` | CI gates | yes |
| `eval/results/<YYYYMMDD-HHMM>_<kind>_<label>_<split>.json` | metric summary per run | yes |
| `eval/results/details/…jsonl` | per-question outputs | no |
| `docs/results.md` | run log table (rows appended with `--record`) | yes |

`snapshot_id` = crawl start date `YYYY-MM-DD`. `index_version` = `<snapshot_id>-v<N>`, with N starting at 1 and bumped on any rebuild.

### Records

**Manifest line** (`manifest.jsonl`):
`{url, lang: "en"|"ar", page_id, pair_url: str|null, category, depth, title, fetched_at (ISO), http_status, sha256, raw_path}`

**Chunk** (`chunks.jsonl`):
`{chunk_id, page_id, url, lang, pair_url, title, heading_path, text, snapshot_id, category}`
- `chunk_id` = `"<lang>:<page_id>:<i>"`, with i the 0-based chunk number within the page.
- `page_id` = URL path minus the leading `/en` or `/ar`, lowercased, no trailing slash, e.g. `information-and-services/visa-and-emirates-id/emirates-id`. Shared by both language versions.
- `heading_path` = `"<title> > <H2> > <H3>"` (missing levels omitted). `text` starts with that line, then a newline, then the body.

**Eval question** (`eval/questions.jsonl`, D34):
`{id, lang, type, category, turns: [str], gold_page_ids: [str], reference_answer, key_facts: [str], answerable: bool, split: "dev"|"test", origin: "human"|"llm_assisted"|"feedback", notes}`
- `id` = `"q001"`…; `type` ∈ `single`, `multi_turn`, `unanswerable_near`, `unanswerable_oos`, `mixed_script`.
- Unanswerable: `gold_page_ids` = `[]`, `key_facts` = `[]`, `reference_answer` = `""`.

### Modules (`src/arengov/`) and signatures

| Module | Phase | Public functions |
|---|---|---|
| `config.py` | 00 | constants below; calls `dotenv.load_dotenv()` |
| `__main__.py` | 00 | argparse CLI; each phase adds its subcommands |
| `crawl.py` | 01 | `normalize_url(href, base) -> str\|None`, `category_of(url) -> str\|None`, `mirror_url(url) -> str`, `page_id(url) -> str`, `crawl(snapshot_id, client=None) -> Path`, `diff(old_dir, new_dir) -> dict` |
| `clean.py` | 02 | `clean_html(html) -> tuple[str, str]` (title, markdown) |
| `chunk.py` | 02 | `count_tokens(text) -> int`, `chunk_page(title, markdown, meta) -> list[dict]` |
| `index.py` | 02 | `build_index(snapshot_id, index_version) -> Path` (08 adds `embed=False`), `load_index(version=None) -> Index` (dataclass: `chunks`, `langs` np.array [02]; `bm25`, `bm25_nonorm` lazy [03]; `embeddings` [08]; auto-download when missing [15]) |
| `text_ar.py` | 03 | `detect_lang(text) -> "ar"\|"en"`, `normalize_ar(text) -> str`, `tokenize(text, normalize=True) -> list[str]` |
| `bm25.py` | 03 | `class BM25(docs_tokens, k1, b)` with `.search(query_tokens, top_n, mask=None) -> list[tuple[int, float]]` |
| `llm.py` | 04 | `LLMResult` dataclass `(text, input_tokens, output_tokens, latency_ms, cost_usd, model)`; `complete(system, messages, max_tokens, *, role="gen", json_schema=None) -> LLMResult` |
| `generate.py` | 04 | `build_prompt(question, chunks, answer_lang) -> tuple[str, list]`, `parse_citations(text, n) -> tuple[str, list[int], list[int]]`, `refusal_message(lang) -> str`, `generate(question, chunks, answer_lang) -> dict` |
| `pipeline.py` | 03 | `retrieve(query, *, lang_filter=None, mode=…, use_rerank=True, use_norm=True) -> dict` (03: only `mode="bm25"`, which is the default until 08 makes `"hybrid"` the default); 04 adds `answer(messages, answer_lang="auto") -> dict` |
| `evalset.py` | 05 | `sample_pages(n, seed)`, `validate(path) -> list[str]` (errors), `assign_splits(path, seed)` |
| `eval_retrieval.py` | 06 | `run(split, *, mode, use_rerank, use_norm, cross_lingual, label, record) -> dict` |
| `eval_answers.py` | 07 | `run(split, *, backend, label, record) -> dict` |
| `judge.py` | 07 | `judge(question, chunks, answer, reference_answer, key_facts) -> dict`; phase 11 adds `export_blind`, `agreement` |
| `embed.py` | 08 | `embed_texts(texts, batch_size=16) -> np.ndarray`, `embed_query(text) -> np.ndarray` |
| `retrieve.py` | 08 | `dense_search(qvec, embeddings, top_n, mask=None)`, `rrf(rankings, k) -> list[tuple[int, float]]`; phase 09 adds `collapse_pairs(ranked, chunks)` |
| `rerank.py` | 09 | `rerank(query, chunks, idxs) -> list[tuple[int, float]]` (sigmoid scores, desc) |
| `rewrite.py` | 10 | `rewrite(prev_user_msgs, question, lang) -> tuple[str, LLMResult]` |
| `scrub.py` | 12 | `scrub(text) -> str` |
| `tracing.py` | 12 | `init_tracing(project)`, `span(name, **attrs)` context manager (no-op when Phoenix isn't configured) |
| `api.py` | 13 | FastAPI `app` |

**`pipeline.retrieve` returns** `{"candidates": [(idx, score)…] (top FUSED_TOP_N after fusion, or BM25 when mode="bm25"), "ranked": [(idx, score)…] (after rerank+collapse, ≥10 long when available), "final": ranked[:TOP_K_CONTEXT], "top_score": float|None (best rerank score, None without reranker), "stages": {"bm25": […], "dense": […]}}`. `idx` = row in `Index.chunks`.

**`pipeline.answer` returns** `{answer, citations: [{n, url, title, lang, snippet, pair_url}], refused: bool, refusal_reason: None|"gate"|"no_answer", invalid_citations: [int] (out-of-range [n] the generator removed; added in phase 07), lang, rewritten_query, final_chunk_ids: [str], usage: {input_tokens, output_tokens, cost_usd}, latency_ms, snapshot_id, span_id: str|None, _chunks: [chunk dicts]}` (`span_id` is set from phase 12, None when tracing is off; `_chunks` = the final chunks the generator saw, added in phase 07 for the judge, internal, stripped by the API). For a refusal, `answer` is the localized refusal message and `citations` lists up to 3 closest distinct pages, numbered 1–3.

### Git workflow

`main` is always green. Each phase works on branch `phase-NN-<name>` (from an up-to-date `main`), commits, pushes, and opens a PR with `gh pr create` (title `Phase NN: <name>`, body = the HANDOFF "Done" + "Metrics"). The owner merges after CI is green. Commit messages: `phase NN: <what>`.

### Config constants (`config.py`; the phase that adds each is in brackets)

```
[00] ROOT, DATA_DIR, SNAPSHOT_ROOT, INDEX_ROOT, EVAL_DIR, INDEX_VERSION_FILE
[01] BASE_URL="https://u.ae", CATEGORIES=("visa-and-emirates-id","jobs","business"),
     CRAWL_DELAY_S=3.0, CRAWL_MAX_DEPTH=4, CRAWL_MAX_EN_PER_CATEGORY=70,
     CRAWL_MAX_CONSECUTIVE_ERRORS=3, CRAWL_TIMEOUT_S=30,
     USER_AGENT="ArEnGovRAG/0.1 (+https://github.com/Mazenghonem1/arengov-rag; non-commercial research)"
[02] MIN_PAGE_CHARS=200, CHUNK_MAX_TOKENS=400, TOKENIZER_MODEL="BAAI/bge-m3"
[03] BM25_K1=1.5, BM25_B=0.75, BM25_TOP_N=50, TOP_K_CONTEXT=5
[04] LLM_BACKEND=os.environ.get("LLM_BACKEND","openai"), GEN_MODEL="gpt-6-luna",
     JUDGE_MODEL=os.environ.get("JUDGE_MODEL","gpt-6.1-terra"), OLLAMA_MODEL="qwen3:8b", OLLAMA_BASE_URL="http://localhost:11434/v1",
     REASONING_EFFORT=<lowest value the API accepts, found in phase 04>,
     GEN_MAX_TOKENS=1024, PRICES_PER_M={"gpt-6-luna": (0.10, 0.50), "gpt-6.1-terra": (1.00, 5.00)},
     SNIPPET_MAX_CHARS=300
[07] JUDGE_MAX_TOKENS=800
[08] EMBED_MODEL="BAAI/bge-m3", DENSE_TOP_N=50, RRF_K=60, FUSED_TOP_N=20
[09] RERANK_MODEL="BAAI/bge-reranker-v2-m3", RERANK_TOP_N=20, RERANK_MAX_LENGTH=512, GATE_TAU=<from data>
[10] HISTORY_MAX_TURNS=3, REWRITE_MAX_TOKENS=200
[13] QUESTION_MAX_CHARS=500, RATE_LIMIT_PER_HOUR=20, DAILY_CAP=100
```

### Metric keys (used in summaries, `thresholds.json`, `docs/results.md`)

Retrieval: `recall@5`, `recall@20`, `mrr@10`, computed on answerable questions only (types `single`, `multi_turn`, `mixed_script`); a hit = any gold `page_id` in the list. Answers: `refusal_correct`, `lang_match`, `citation_valid`, `faithfulness`, `correctness`, `citation_accuracy`, `latency_p50_ms`, `latency_p95_ms`, `cost_per_q_usd`. All rates are 0–1 floats in JSON and percentages in `docs/results.md`.

### CLI subcommands (`uv run python -m arengov <cmd>`)

`crawl`, `diff`, `build-index`, `search`, `ask`, `sample-pages`, `validate-eval`, `assign-splits`, `eval-retrieval`, `eval-answers`, `set-thresholds`, `check-thresholds`, `pick-tau`, `judge-export`, `judge-agreement`, `upload-index`, `download-index`. The ops scripts live in `scripts/` (`ops_report.py`, `export_bad_feedback.py`).

**LLM flags (D67, D68):** `ask` uses `LLM_BACKEND` from the environment (`ollama` locally, so ad-hoc testing is free). The eval commands (`eval-retrieval`, `eval-answers`, `pick-tau`) take `--backend openai|ollama` **defaulting to `openai`**. `eval-answers` also takes `--judge-model` (default `config.JUDGE_MODEL` = `gpt-6.1-terra`; every phase uses the default). Every answer summary records `backend`, `gen_model` and `judge_model`.

## Estimated OpenAI spend

Budget: **$5 total credit** (D66). Unit costs are estimated from the 2026-11-09 prices (D68): a `gpt-6-luna` answer ≈ $0.0005, a `gpt-6.1-terra` judgment ≈ $0.0045. An answer eval costs ≈ $0.08 on test (20 q, ~16 judged) and ≈ $0.16 on dev (40 q). Phase 04 measures the real cost per query; if it's above $0.001, recompute this table in HANDOFF.

| Where | What | Est. |
|---|---|---|
| 04 | reasoning-effort probe + 2 OpenAI smoke calls (rest on Ollama) | $0.01 |
| 07 | answer baseline dev + test | $0.24 |
| 08 | answer eval test | $0.08 |
| 09 | answer eval test | $0.08 |
| 10 | answer evals dev + test, rewrites in retrieval evals, τ re-pick, demo checks | $0.26 |
| 11 | only if the judge prompt is revised: re-judge ~45 answers once | $0–0.20 |
| 15 | CI retrieval evals (~$0.001 each × ~30) + ~3 manual answer-eval dispatches | $0.27 |
| 16 | live smoke test + 20-request latency probe | $0.03 |
| 17 | Qwen row judging (+ one luna re-run if phase 16 changed the pipeline) | $0.07–0.15 |
| **Development total** | | **≈ $1.0–1.3** |
| Live demo | ≤ 100 questions/day × ~$0.0005 (worst case ≈ $1.50/month) | rest of the credit |

Each phase's HANDOFF records its OpenAI spend (from eval summaries and the OpenAI dashboard), so drift shows up early.
