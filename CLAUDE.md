# arengov-rag

A bilingual Arabic–English RAG assistant over public UAE government-services pages (u.ae: visa & Emirates ID, jobs, business). Users ask in Arabic or English and get a grounded answer with numbered citations, in their language, even when the best source is in the other language. It's a junior AI-engineer portfolio project: the owner must understand every line, so the core pipeline is plain Python and every step stays visible.

## Stack

Python 3.12, `uv`, `pytest`, `ruff`. httpx + BeautifulSoup/lxml (crawl/clean), hand-written BM25 + `snowballstemmer`, `BAAI/bge-m3` dense embeddings + `BAAI/bge-reranker-v2-m3` via `sentence-transformers`, NumPy brute-force search, `openai` SDK (OpenAI `gpt-6-luna` generator, `gpt-6.1-terra` judge for every judged run; local `qwen3:8b` through Ollama's OpenAI-compatible endpoint), FastAPI + one static `ui/index.html`, Arize Phoenix tracing, Docker Compose, GitHub Actions, Hugging Face Spaces.

## Where things are

- `docs/PLAN.md`: phases, hours, **architecture contracts** (paths, record schemas, function signatures, config names). The single source of truth for interfaces.
- `docs/phases/phase-NN-<name>.md`: one self-contained phase each.
- `docs/HANDOFF.md`: state left by the previous phase.
- `docs/DECISIONS.md`: every design decision (D1…) with its reason. Read it when a phase file cites a D-number you need more detail on.
- `docs/PRD.md`: goal, scope, non-goals, success metrics.

## Commands

```
uv sync                                  # install
uv run pytest -m "not slow"              # fast tests (no network, no models)
uv run pytest                            # all tests
uv run ruff check . && uv run ruff format --check .
uv run python -m arengov --help          # the one CLI (crawl, build-index, search, ask, eval-…)
```

## Conventions

- Flat modules in `src/arengov/`, one per pipeline stage. No LangChain/LlamaIndex, no extra frameworks, no abstraction layers or config systems: constants live in `src/arengov/config.py`, secrets in env vars (`.env` locally).
- Smallest complete change. A shortcut with a known limit gets a comment `# shortcut: <limit>, <when to upgrade>`.
- Every non-trivial function gets a small test. Tests that load models or hit the network are marked `@pytest.mark.slow`.
- Comments explain why, in one line.

## Hard rules

- **Public data only, politely.** The crawler identifies itself, waits 3 s between requests, and stops on repeated errors. Nothing from the owner's employer: no company code, data, prompts or designs.
- **Crawled content stays out of git.** `data/` is gitignored. Test fixtures are synthetic HTML with invented text. The UI shows answers + ≤300-char snippets + source links only.
- **No personal data.** Queries are scrubbed before tracing; IPs are never logged.
- **Disclaimer everywhere it's user-facing:** not official advice, info may be outdated, always check the linked source page.
- **OpenAI credit is $5 in total.** Debug and test ad hoc with `LLM_BACKEND=ollama` (free, local GPU). Spend OpenAI only on recorded eval runs, the checks a phase file names, and the deployed demo. Eval commands default to `--backend openai` and the `gpt-6.1-terra` judge. Record each phase's OpenAI spend in HANDOFF.
- **The index is versioned.** CI never crawls or rebuilds the index. Changing cleaning/chunking/embedding means rebuilding locally, uploading a new index version, and bumping `eval/index_version.txt` in the same commit.

## Working rules (one phase per session)

1. **Start:** read `CLAUDE.md`, `docs/PLAN.md`, `docs/HANDOFF.md`, and the current phase file. Restate the goal and your plan in a few lines, then **wait for the owner's "go"**. On "go": `git switch main && git pull`, then `git switch -c phase-NN-<name>` (see PLAN.md § Git workflow).
2. **During:** follow the phase file. It already contains the design decisions. When something it needs is missing or contradicts reality, collect the questions and ask them **in one batch**, each with a recommended default, instead of guessing.
3. **End:** run tests and the evals the phase names; update `docs/HANDOFF.md` (done, deviations, metrics, open issues, notes for next phase); commit, push, open the PR; then stop and tell the owner to merge once CI is green and `/clear` before the next phase.
4. Start the next phase only when the owner asks for it in a new session.
5. Tasks marked **[YOU]** are the owner's. Explain exactly what to do, then wait.
6. From phase 15 on: when a phase changes generation-related files (`generate.py`, `llm.py`, `rewrite.py`, `pipeline.py`, `retrieve.py`, `rerank.py`, `judge.py`, `eval_answers.py`, `config.py`, `eval/*`), trigger the answer gate manually with `gh workflow run eval-answers.yml --ref <branch>` and report its result in the PR.
