# Phase 12: Tracing with Phoenix, and PII scrubbing

**Size:** ~3 h · **Depends on:** phase 11 merged; **Docker Desktop installed and running** [YOU]

## Goal

Every `ask` produces one Phoenix trace with a span per pipeline stage (rewrite, BM25, dense, fusion, rerank, collapse, generate) carrying the data needed to debug it. Eval runs go to a separate project, and personal data is scrubbed before it reaches anything.

## Decisions that apply

- Tool: Arize Phoenix, self-hosted; locally as a Docker Compose service (D39). The app container comes in phase 14; this phase runs the CLI on the host against Phoenix in Docker.
- Instrumentation (D40): `arize-phoenix-otel` `register(...)` + `openinference-instrumentation-openai` for LLM calls, plus manual spans via OpenTelemetry. Project `arengov` for real use, `eval` for eval runs.
- Span tree:
  - `ask` (root, OpenInference span kind `CHAIN`)
    - `rewrite` (CHAIN; only with history)
    - `retrieve.bm25`, `retrieve.dense`, `fuse`, `rerank`, `collapse` (each kind `RETRIEVER`)
    - `generate` (CHAIN; the auto-instrumented LLM span nests under it)
- Root attributes: `input.value` (the scrubbed question), `output.value` (the answer), `arengov.lang`, `arengov.answer_lang`, `arengov.rewritten_query`, `arengov.refused`, `arengov.refusal_reason`, `arengov.cost_usd`, `arengov.input_tokens`, `arengov.output_tokens`, `arengov.latency_ms`, `arengov.snapshot_id`, `arengov.index_version`, `arengov.git_sha`.
- RETRIEVER span attributes: for the top 10 items, `retrieval.documents.{i}.document.id` (chunk_id), `.document.score`, `.document.metadata` (JSON with page_id, lang, url).
- `generate`: `input.value` = the full user prompt (sources + question), `output.value` = the raw model text.
- **Tracing is optional:** with no `PHOENIX_COLLECTOR_ENDPOINT` set, nothing is exported and nothing breaks. Tests and CI run without Phoenix. (OpenTelemetry's default tracer is a no-op.)
- **Scrubbing** (D43, D62): `scrub(text)` runs at the **start of `pipeline.answer` on every user message**, so PII never reaches retrieval, the LLM or any span. Patterns, applied in this order, each replaced with `[REDACTED]`:
  1. email `[\w.+-]+@[\w-]+\.[\w.-]+`
  2. Emirates ID `784[-\s]?\d{4}[-\s]?\d{7}[-\s]?\d`
  3. phone `(?:\+|00)?\d[\d\s-]{7,}\d`
  4. passport-like `\b[A-Za-z]\d{6,9}\b`
  5. any run of ≥ 8 digits `\d{8,}`
  Apply them after mapping Arabic-Indic digits to ASCII **for matching only**: build a translated copy, find match spans in it, and redact the same spans in the original. That works because the digit mapping is 1:1 in length.
- `pipeline.answer` returns `span_id` = the root span's id as 16 hex chars, or `None` when tracing is off (an invalid span context) (PLAN.md contract).
- Phoenix data retention: 30 days (D43).

## Tasks

1. `uv add arize-phoenix-otel openinference-instrumentation-openai opentelemetry-api`.
2. **`docker-compose.yml`** with service `phoenix`:
   - image `arizephoenix/phoenix:<pinned tag>` (look up the current release on Docker Hub; never use `latest`);
   - ports `6006:6006` (UI + OTLP HTTP) and `4317:4317` (OTLP gRPC);
   - named volume `phoenix_data` mounted at `/mnt/data`, with env `PHOENIX_WORKING_DIR=/mnt/data`;
   - 30-day retention: find the setting in the docs for the pinned version (an env var for the default retention policy, or the UI). Use the env var if there is one, otherwise do it in the UI and note the steps in HANDOFF.
3. **`src/arengov/scrub.py`:** `scrub(text)` as specified.
4. **`src/arengov/tracing.py`:**
   - `init_tracing(project)`: if `PHOENIX_COLLECTOR_ENDPOINT` is unset, return. Otherwise `tp = register(project_name=project, endpoint=f"{endpoint}/v1/traces", batch=True)` (check the signature of the installed version; pass the `PHOENIX_API_KEY` header if set), then `OpenAIInstrumentor().instrument(tracer_provider=tp)`. Make it idempotent (a module flag).
   - `span(name, kind="CHAIN", **attrs)`: a context manager over `trace.get_tracer("arengov").start_as_current_span(name)`. It sets `openinference.span.kind` and the attrs (non-primitive values JSON-dumped) and yields the span.
   - `set_docs(span, ranked, chunks, k=10)`: writes the `retrieval.documents.*` attributes.
   - `GIT_SHA`: from env `GIT_SHA`, else `git rev-parse --short HEAD`, else `"unknown"`, computed once.
5. **Instrument `pipeline.py`:**
   - `answer()`: scrub the messages first, then wrap everything in `span("ask")`; set the root attributes at the end and capture `span_id`.
   - Wrap each stage of `retrieve()` in its span. Wrap `rewrite` and `generate` calls in spans with their attributes.
   - Keep the stage logic unchanged.
6. **CLI:** `ask` calls `init_tracing("arengov")`; `eval-retrieval`, `eval-answers` and `pick-tau` call `init_tracing("eval")`.
7. **Tests:**
   - `tests/test_scrub.py`: each pattern (an EN sentence with an email; `784-1990-1234567-1` and `784199012345671`; `+971 50 123 4567`; passport `N1234567`; a 9-digit number; an Arabic sentence with an Arabic-Indic Emirates ID `٧٨٤١٩٩٠١٢٣٤٥٦٧١`, redacted while the Arabic words stay intact); fees like `AED 1,000` and `30 days` untouched.
   - `tests/test_tracing.py`: with no endpoint, `pipeline.answer` (faked stages) returns `span_id is None` and works. With an in-memory span exporter (`opentelemetry.sdk.trace.export.in_memory_span_exporter`) installed on a test tracer provider: the span names and parent-child structure match the tree above, the root attributes are present, and the question attribute is scrubbed.
8. **Manual check:** `docker compose up -d phoenix`; set `PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006` in `.env`; `ask` 3 questions on Ollama (`LLM_BACKEND=ollama`, free; the OpenAI instrumentor also traces Ollama calls, since they go through the `openai` SDK): EN, AR, and one with a fake Emirates ID in it; run `eval-retrieval --split dev --label trace-check` (no `--record`). Open http://localhost:6006 and confirm: project `arengov` has 3 traces with all spans; the retriever spans show documents; the LLM span shows tokens; the ID appears as `[REDACTED]` everywhere, including the LLM span's input; project `eval` holds the eval traces. Show the owner one trace.

## Files

Create: `docker-compose.yml`, `src/arengov/scrub.py`, `src/arengov/tracing.py`, `tests/test_scrub.py`, `tests/test_tracing.py`. Change: `pipeline.py`, `__main__.py`, `.env.example` (example endpoint), `pyproject.toml`, `uv.lock`, `docs/HANDOFF.md`.

## Acceptance criteria

- `uv run pytest -m "not slow"` passes **without Phoenix running**; ruff clean.
- The manual check passes (owner has seen a trace); the PII test question shows `[REDACTED]` in every span.
- `eval-retrieval --split test` with tracing on gives the same metrics as phase 10's `rewrite` row (tracing doesn't change behavior). This is the only OpenAI use in this phase (~$0.002).

## Out of scope

User feedback annotations, the API and the UI are phase 13; the ops report is phase 14. Phoenix runs locally only; the hosted Phoenix is phase 16. Tracing observes the pipeline and leaves its logic and outputs unchanged.

## What you should understand after this phase

- **Traces and spans:** a trace is one request; spans are timed, nested steps with attributes. Why "which stage was slow / which chunk was missing" needs per-stage spans.
- **OpenTelemetry vs Phoenix:** OTel is the vendor-neutral standard for emitting traces; OpenInference adds LLM/RAG conventions (span kinds, retrieval documents); Phoenix is one backend that reads them. Switching backends means changing an endpoint.
- **Auto vs manual instrumentation:** the OpenAI instrumentor captures prompts, tokens and latency for free; pipeline stages need manual spans.
- **Privacy by design:** scrubbing at the entry point protects the LLM provider, the logs and the traces at once, whereas scrubbing logs afterwards always misses a copy.
- **Separate projects for eval and production** keep ops metrics honest.

## Handoff checklist

- [ ] Acceptance criteria pass.
- [ ] HANDOFF: the Phoenix image tag, how retention was set, a screenshot description of one trace, anything Phoenix displayed oddly.
- [ ] Committed on `phase-12-tracing`, pushed, PR open.
- [ ] Told the owner: merge when green, `/clear`, next is phase 13.
