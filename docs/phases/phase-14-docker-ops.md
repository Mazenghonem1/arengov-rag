# Phase 14: App container, Compose stack, ops report, bad-feedback export

**Size:** ~3 h · **Depends on:** phase 13 merged; Docker Desktop running

## Goal

`docker compose up --build` runs the app and Phoenix together. `scripts/ops_report.py` turns traces and feedback into the 4 ops metrics, and `scripts/export_bad_feedback.py` turns thumbs-down traces into eval-case candidates.

## Decisions that apply

- Compose (D46): services `app` + `phoenix`. Ollama stays on the host (GPU), reached at `http://host.docker.internal:11434/v1`. `./data` is mounted read-only for the index.
- The app image is the **same image** HF Spaces will run in phase 16 (D44): `python:3.12-slim`, CPU torch (the Linux source in `pyproject.toml`), models **downloaded at build time**, non-root user with uid 1000, port **7860**.
- Dashboard (D41): Phoenix's built-in views plus `scripts/ops_report.py --days 7`, which writes `docs/ops-report.md` with:
  - number of requests;
  - p50/p95 latency (root `ask` span, `arengov.latency_ms`);
  - mean cost/query (`arengov.cost_usd`);
  - no-answer rate (`arengov.refused`) with the gate vs no_answer split;
  - feedback rate (annotated / requests) and % negative.
- Feedback → eval loop (D42, must-have, manual): `scripts/export_bad_feedback.py --days N` writes thumbs-down traces to gitignored `eval/candidates.jsonl`, one line each, pre-filled with D34 fields: `turns` (the scrubbed question; earlier turns aren't stored server-side, so a single turn), `lang`, `origin: "feedback"`, `split: "dev"`, empty labels for the owner to fill, plus context fields `_span_id`, `_time`, `_answer`, `_final_page_ids`, `_comment`. The owner labels and appends good ones to `questions.jsonl` by hand.

## Tasks

1. **`Dockerfile`:**
   - `FROM python:3.12-slim`; `COPY --from=ghcr.io/astral-sh/uv:<pinned version> /uv /bin/uv`.
   - `WORKDIR /app`; `ENV HF_HOME=/app/.hf UV_COMPILE_BYTECODE=1 PYTHONUNBUFFERED=1`.
   - Copy `pyproject.toml uv.lock .python-version`, then `RUN uv sync --locked --no-dev --no-install-project`.
   - Copy `src/ ui/ eval/index_version.txt` (keeping the paths), then `RUN uv sync --locked --no-dev`.
   - `RUN uv run --no-sync python -c "…"`: download `BAAI/bge-m3` (SentenceTransformer), `BAAI/bge-reranker-v2-m3` (CrossEncoder) and the bge-m3 tokenizer into `HF_HOME`.
   - `RUN useradd -m -u 1000 user && chown -R user /app`; `USER user`; `EXPOSE 7860`.
   - `CMD ["uv", "run", "--no-sync", "uvicorn", "arengov.api:app", "--host", "0.0.0.0", "--port", "7860"]`.
   - Add a `.dockerignore`: `.venv`, `data`, `.git`, `.env`, `eval/results`, `eval/grading`, `tests`, `docs`, caches.
2. **`docker-compose.yml`:** add service `app`:
   - `build: .`, `ports: ["7860:7860"]`, `env_file: .env`;
   - `environment`: `PHOENIX_COLLECTOR_ENDPOINT=http://phoenix:6006`, `OLLAMA_BASE_URL=http://host.docker.internal:11434/v1`, `GIT_SHA=${GIT_SHA:-unknown}`;
   - `volumes: ["./data:/app/data:ro"]`, `depends_on: [phoenix]`.
   - `config.OLLAMA_BASE_URL` must read the env var with the existing value as default; change it if it doesn't.
3. **`scripts/ops_report.py`:** argparse `--days 7 --project arengov --out docs/ops-report.md`. Use the Phoenix client (`PHOENIX_COLLECTOR_ENDPOINT` as base URL) to fetch root `ask` spans in the window and the `user_feedback` annotations (look up the dataframe/query methods in the installed `arize-phoenix-client`). Keep the math in a pure function `compute_metrics(spans: list[dict], annotations: list[dict]) -> dict` and render Markdown: the date range, the metric table, and the refusal split.
4. **`scripts/export_bad_feedback.py`:** argparse `--days N --project arengov --out eval/candidates.jsonl`. Pure function `to_candidates(spans, annotations) -> list[dict]` (score 0 only, newest first). It appends without duplicating `_span_id`s already in the file.
5. **`tests/conftest.py`:** add `scripts/` to `sys.path`. Tests: `tests/test_ops_report.py` (`compute_metrics` on 5 fake spans + 2 annotations: p95, mean cost, refusal rates, feedback rate, % negative; zero spans → "no data" without dividing by zero) and `tests/test_export_feedback.py` (only score-0, dedup, fields present).
6. **Manual check:**
   - `docker compose up --build` (the first build downloads ~5 GB of models; that's expected). Note the image size.
   - Open http://localhost:7860 and ask 5 questions (examples + 1 typed), giving 2 thumbs-down with comments and 1 thumbs-up.
   - Run `uv run python scripts/ops_report.py --days 1` → `docs/ops-report.md` shows n=5 (plus earlier local traffic), a feedback rate and % negative.
   - Run `uv run python scripts/export_bad_feedback.py --days 1` → 2 lines in `eval/candidates.jsonl`.
   - The 5 questions run on Ollama (`LLM_BACKEND=ollama` from `.env`, free, D67), which also proves the container reaches host Ollama. If it's refused, the owner sets the Windows env var `OLLAMA_HOST=0.0.0.0` and restarts Ollama; note it in HANDOFF. Mean cost/query in this local report is $0 (Ollama); live cost numbers come from phase 16. This phase spends no OpenAI credit.

## Files

Create: `Dockerfile`, `.dockerignore`, `scripts/ops_report.py`, `scripts/export_bad_feedback.py`, `tests/conftest.py`, `tests/test_ops_report.py`, `tests/test_export_feedback.py`, `docs/ops-report.md` (a local sample; regenerated from live traffic in phase 17). Change: `docker-compose.yml`, `config.py` (if needed), `docs/HANDOFF.md`.

## Acceptance criteria

- `uv run pytest -m "not slow"` passes; ruff clean.
- `docker compose up --build` serves the UI on :7860 with traces in Phoenix on :6006.
- `docs/ops-report.md` is generated with all 4 metrics; `eval/candidates.jsonl` gets the thumbs-down items and is gitignored.
- The container reaches host Ollama (or the fix is documented).

## Out of scope

The container reads the index from the mounted `./data`; downloading it from HF is phase 15. CI and deployment are phases 15–16. The dashboard is Phoenix + the Markdown report (D4: no custom dashboard page).

## What you should understand after this phase

- **Docker image layers and caching:** dependencies first, code last; why models are baked in at build time (fast cold starts, no runtime download).
- **Compose networking:** services reach each other by name (`phoenix:6006`); `host.docker.internal` reaches the host machine.
- **CPU vs CUDA torch** and why the deploy image uses CPU wheels (smaller image, no GPU on the host).
- **Ops metrics from traces:** p95 vs mean latency, cost per query, no-answer rate as a quality signal, feedback rate as an engagement signal.
- **Closing the loop:** a real user's thumbs-down becomes a labeled eval case, then a regression test.

## Handoff checklist

- [ ] Acceptance criteria pass.
- [ ] HANDOFF: the image size, build time, the ops-report numbers, the Ollama-from-container result, the Phoenix client methods used.
- [ ] Committed on `phase-14-docker-ops`, pushed, PR open.
- [ ] Told the owner: merge when green, `/clear`, next is phase 15 (needs a Hugging Face write token).
