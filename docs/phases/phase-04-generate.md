# Phase 04: LLM client, cited answers, refusal: the minimal pipeline

**Size:** ~4 h · **Depends on:** phase 03 merged; `OPENAI_API_KEY` in `.env`; Ollama running with `qwen3:8b`

## Goal

`uv run python -m arengov ask "<question>"` answers from the top-5 BM25 chunks with `[n]` citations in the question's language, or refuses with `NO_ANSWER` → a localized refusal plus related links. It works with OpenAI and with local Ollama.

## Prerequisites

- Phase 03 merged. `.env` has `OPENAI_API_KEY` (owner, phase 00). `ollama list` shows `qwen3:8b`.

## Decisions that apply

- Generator `gpt-6-luna`, local `qwen3:8b`; backend via `LLM_BACKEND=openai|ollama` (D27, D68). Judge model = `config.JUDGE_MODEL`, which reads env `JUDGE_MODEL` and defaults to `gpt-6.1-terra`, the one judge used everywhere (D68). Prices per 1M tokens: luna $0.10 in / $0.50 out, terra $1.00 / $5.00 (checked 2026-11-09).
- **Budget (D66, D67):** $5 of OpenAI credit in total. Ad-hoc testing uses `LLM_BACKEND=ollama`; this phase makes only the few OpenAI calls listed in tasks 2, 8 and 9.
- **One client** (D29): the `openai` SDK Chat Completions API for both backends; Ollama through `base_url=OLLAMA_BASE_URL`, `api_key="ollama"`. Ollama: append `"\n/no_think"` to the system prompt and strip `<think>…</think>` (regex, DOTALL) from the output. Ollama cost = 0.
- `role="judge"` **always** uses OpenAI with `config.JUDGE_MODEL` (read at call time, so a CLI flag can override it), whatever `LLM_BACKEND` says (D28, D68).
- Prompt (D26): numbered context blocks; cite `[n]` after every factual sentence; answer in the target language (MSA for Arabic); exactly `NO_ANSWER` when the sources lack the answer. Plain-text output; parse `[n]` with a regex; remove and log out-of-range markers.
- Answer language = `answer_lang` if given, else `detect_lang(question)` (D15).
- Refusal: the localized message + up to 3 closest distinct pages from the retrieved chunks, as citations numbered 1–3 (PLAN.md § `pipeline.answer` returns). The retrieval gate (layer a of D26) arrives in phase 09.

## Tasks

1. `uv add openai`. Add the `[04]` constants to `config.py`.
2. **Find `REASONING_EFFORT`:** call `gpt-6-luna` with a 1-line prompt and `reasoning_effort` set to `"none"`, then `"minimal"`, then `"low"`; the first value that doesn't return a 400 goes into `config.REASONING_EFFORT`. Record it in HANDOFF.
3. **`src/arengov/llm.py`:**
   - `@dataclass LLMResult(text, input_tokens, output_tokens, latency_ms, cost_usd, model)`.
   - `complete(system, messages, max_tokens, *, role="gen", json_schema=None)`:
     - Pick backend and model: `role == "judge"` → openai + `config.JUDGE_MODEL`; else `config.LLM_BACKEND` (read at call time) → openai + `GEN_MODEL` or ollama + `OLLAMA_MODEL`.
     - Clients: cached per backend; `timeout=60`; SDK default retries.
     - OpenAI kwargs: `model`, `messages=[{"role": "system", "content": system}, *messages]`, `max_completion_tokens=max_tokens`, `reasoning_effort=REASONING_EFFORT`. With `json_schema`: `response_format={"type": "json_schema", "json_schema": {"name": "result", "schema": json_schema, "strict": True}}`.
     - Ollama kwargs: `model`, the same messages with `/no_think` appended to the system content, `max_tokens=max_tokens`.
     - Measure latency with `time.perf_counter`. Tokens come from `resp.usage.prompt_tokens` / `completion_tokens`. Cost = `in * p_in / 1e6 + out * p_out / 1e6` from `PRICES_PER_M` (0 if the model isn't listed). If `finish_reason == "length"`, log a warning.
4. **`src/arengov/generate.py`:**
   - `SYSTEM_PROMPT` (exact text):
     ```
     You answer questions about UAE government services using only the numbered sources in the user message.
     Rules:
     1. Use only facts stated in the sources. If the sources do not contain the answer, reply with exactly: NO_ANSWER
     2. After every sentence that states a fact, cite its source number in square brackets, like [2]. Use several, like [1][3], when needed. Cite only numbers that exist.
     3. Write the whole answer in the language named on the last line of the user message, even when the sources are in another language. Write Arabic in Modern Standard Arabic.
     4. Be concise: at most about 150 words. Use a short list for steps or required documents.
     5. Add nothing that is not in the sources: no advice, no opinions, no outside knowledge.
     ```
   - `build_prompt(question, chunks, answer_lang)` → `(SYSTEM_PROMPT, [{"role": "user", "content": …}])`, where the content is:
     ```
     Sources:
     [1] (en) <title> - <url>
     <chunk text>

     [2] (ar) …

     Question: <question>
     Answer language: English|Arabic
     ```
   - `parse_citations(text, n)`: regex `\[([0-9٠-٩]+)\]`; map Arabic-Indic digits to ASCII; keep markers with 1 ≤ k ≤ n (rewritten in ASCII digits); delete the others. Returns `(clean_text, sorted unique valid ks, invalid ks)`.
   - `REFUSAL = {"en": "I couldn't find the answer in the u.ae pages I have. These pages may be related:", "ar": "لم أجد الإجابة في صفحات u.ae المتوفرة لدي. قد تكون هذه الصفحات ذات صلة:"}`; `refusal_message(lang)` returns it.
   - `generate(question, chunks, answer_lang)` → `{"answer", "cited", "invalid_citations", "no_answer", "llm"}`. `no_answer` = `"NO_ANSWER"` appears in the raw text. Calls `complete(..., GEN_MAX_TOKENS)`.
5. **`pipeline.answer(messages, answer_lang="auto")`:**
   - question = content of the last `role == "user"` message; lang = `answer_lang` unless `"auto"`, else `detect_lang(question)`.
   - `r = retrieve(question)`; chunks = the `final` chunk dicts.
   - `g = generate(question, chunks, lang)`.
   - Not `no_answer`: citations = for each cited n, `{n, url, title, lang, snippet, pair_url}` of chunk n-1. Snippet = chunk text without its first (heading) line, cut to `SNIPPET_MAX_CHARS` at a word boundary, with "…" if cut.
   - `no_answer`: `refused=True`, `refusal_reason="no_answer"`, answer = `refusal_message(lang)`, citations = the first 3 distinct pages (by `page_id`) among the final chunks, numbered 1–3.
   - Fill every field of the PLAN.md return dict (`rewritten_query = question`, `span_id = None`). `latency_ms` covers the whole call. `snapshot_id` comes from the chunks.
6. **CLI:** `ask "QUESTION" [--lang auto|ar|en] [--backend openai|ollama]`. `--backend` sets `config.LLM_BACKEND` before the call. Print: the answer, numbered citations (title + url), refused/reason, tokens, cost, latency.
7. **Tests** (`tests/test_generate.py`, `tests/test_llm.py`, `tests/test_pipeline.py`; no network, monkeypatch `llm.complete` / the OpenAI client):
   - `parse_citations`: valid kept, `[9]` with n=5 removed and reported, `[٢]` → `[2]`, duplicates collapse.
   - `build_prompt`: numbering, `(lang)` tags, last line `Answer language: Arabic` for `"ar"`.
   - `generate`: fake `NO_ANSWER` → `no_answer=True`.
   - `llm.complete`: the ollama path strips `<think>` and appends `/no_think`; `role="judge"` uses OpenAI even with `LLM_BACKEND=ollama`; cost is computed from a fake usage object.
   - `pipeline.answer` with `retrieve` and `complete` faked: citations mapped to the right chunks; the refusal path returns ≤3 distinct pages; `lang` auto-detected.
8. **Manual smoke test.** First with `--backend ollama` (free): 2 EN questions, 2 AR questions, 1 off-topic ("best shawarma in Dubai"). Then **only 2 OpenAI calls** (1 EN, 1 AR, `--backend openai`; cost < $0.01) to verify the OpenAI path and measure the real cost per query. Show the owner. Note anything odd (language drift, missing citations). If the measured OpenAI cost per query is above $0.001, flag it in HANDOFF (PLAN.md § Estimated OpenAI spend assumes ~$0.0005).
9. **Judge model probe** (one call, < $0.01): call `gpt-6.1-terra` once with `role="judge"`, a tiny JSON schema (`{"ok": boolean}`, strict) and the chosen `REASONING_EFFORT`. If the model rejects `reasoning_effort` or `response_format` json_schema, record exactly what failed in HANDOFF; phase 07 depends on both.

## Files

Create: `src/arengov/llm.py`, `src/arengov/generate.py`, `tests/test_llm.py`, `tests/test_generate.py`, `tests/test_pipeline.py`. Change: `pipeline.py`, `config.py`, `__main__.py`, `pyproject.toml`, `uv.lock`, `docs/HANDOFF.md`.

## Acceptance criteria

- `uv run pytest -m "not slow"` passes; ruff clean.
- The smoke test shows: on Ollama, EN→EN and AR→AR answers with ≥1 valid citation each and the off-topic question refused (`NO_ANSWER`); the 2 OpenAI calls answer with valid citations; the printed cost per OpenAI question is <$0.005.

## Out of scope

Retrieval stays BM25-only (dense/rerank come in phases 08–09, measured against the baseline). Each `ask` is single-turn; follow-ups are phase 10. No tracing, API or UI yet.

## What you should understand after this phase

- **Grounded generation:** the prompt makes the LLM a reader of your sources, not a knowledge base. Why "only the sources" plus an explicit `NO_ANSWER` escape hatch reduces hallucination.
- **Citations as a contract:** numbered blocks in, `[n]` out, validated by code. A citation number the model invents gets caught, not shown.
- **Reasoning effort / thinking tokens:** they cost money and latency; for short grounded answers the lowest setting is enough.
- **Token accounting:** input vs output tokens and how cost per query is computed (about $0.001 here).
- **One client, two backends:** the OpenAI-compatible API lets a local model drop in by changing `base_url`.

## Handoff checklist

- [ ] Acceptance criteria pass.
- [ ] HANDOFF: `REASONING_EFFORT` value; smoke-test summary (per question: language ok?, citations, refused?, cost, latency) for both backends; measured OpenAI cost per query; OpenAI spend.
- [ ] Committed on `phase-04-generate`, pushed, PR open.
- [ ] Told the owner: merge when green, `/clear`, next is phase 05. **Phase 05 needs ~7 h of your own time to write questions.**
