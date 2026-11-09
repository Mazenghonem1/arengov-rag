# Phase 13: FastAPI backend, bilingual UI, feedback, rate limits

**Size:** ~4.5 h · **Depends on:** phase 12 merged; `ui/examples.json` from phase 10

## Goal

`uv run uvicorn arengov.api:app --port 8000` serves a single-page bilingual chat UI and a JSON API. It has the demo example buttons, cited answers with snippets, thumbs feedback stored as Phoenix annotations, browser-only history, the disclaimer, and spend guardrails.

## Decisions that apply

- API (D45): `POST /api/ask`, `POST /api/feedback`, `GET /api/health`; static UI served at `/`. No streaming; the UI shows a spinner.
- Guardrails (D30):
  - `QUESTION_MAX_CHARS = 500`;
  - the pipeline uses ≤ 3 previous user turns (already in `pipeline`);
  - per-IP `RATE_LIMIT_PER_HOUR = 20` for `/api/ask` (separate 60/hour for feedback);
  - global `DAILY_CAP = 100` asks per UTC day → HTTP 503 `{"error": "demo_quota"}` (D66);
  - in-memory only.
- **Credit exhaustion (D66):** the owner has $5 of OpenAI credit in total. When an OpenAI call fails with exhausted quota (`openai.RateLimitError` whose error code is `insufficient_quota`), `/api/ask` returns the same 503 `{"error": "demo_quota"}`, so the UI shows "demo paused" instead of an error. Other OpenAI errors stay 500 `internal`.
- Manual UI checks run on Ollama (`LLM_BACKEND=ollama` in `.env`, free) except the final example check in task 5, which uses OpenAI because the demo runs on it (D67).
- IPs are never logged or traced. The limiter keys on `sha256(salt + ip)` with a random salt made at process start (D43). Client IP = the first value of `X-Forwarded-For` when present (HF Spaces sits behind a proxy), else `request.client.host`.
- Feedback (D41): `{span_id, score: 0|1, comment?}` → Phoenix span annotation `user_feedback`, annotator kind `HUMAN`, label `"up"`/`"down"`, score 1/0, explanation = `scrub(comment)`. When tracing is off it's a no-op returning 204.
- UI (D45): one static `ui/index.html` with inline vanilla JS and CSS, no build step, no framework, no external scripts. It has:
  - per-message `dir="auto"` and a `lang` attribute;
  - the example buttons from `ui/examples.json` (the `ar_followup` button appears only after the `ar` example has been answered);
  - an answer-language switch (Auto / العربية / English);
  - `[n]` rendered as links to numbered citations;
  - for each citation: title, URL, language badge, a collapsible snippet (≤300 chars), and an "also in العربية/English" link to `pair_url`;
  - thumbs up/down per answer;
  - a "New chat" button;
  - localStorage history under key `arengov.chat.v1`;
  - the disclaimer banner (text below), the snapshot date, and the privacy note under the input.
- History lives in the browser only (D3). The UI sends the whole conversation (user + assistant messages) each time; the pipeline uses only the user messages (D58).
- **Security:** model output is untrusted. Render text with `textContent` and build citation links as DOM nodes; never put model or user text into `innerHTML`. Only `http(s)://u.ae/...` URLs become links.
- Disclaimer text: identical to `phase-00-setup.md` § Disclaimer text, EN + AR. Privacy note: EN "Don't enter personal information. Questions are logged anonymously to improve quality." / AR "لا تُدخل أي معلومات شخصية. يتم تسجيل الأسئلة دون هوية لتحسين الجودة."

## Tasks

1. `uv add fastapi uvicorn arize-phoenix-client`. Add the `[13]` constants.
2. **`src/arengov/api.py`:**
   - Pydantic models:
     - `Msg {role: Literal["user","assistant"], content: str (1..4000)}`;
     - `AskIn {messages: list[Msg] (1..20), answer_lang: Literal["auto","ar","en"] = "auto"}`, with a validator that the last message is `user` and ≤ `QUESTION_MAX_CHARS`;
     - `FeedbackIn {span_id: str matching ^[0-9a-f]{16}$, score: Literal[0,1], comment: str|None (≤500)}`.
   - Startup (lifespan): `init_tracing("arengov")`; `load_index()`; warm-up = one `embed_query("warm up")` and one `rerank` of one pair, so the first visitor doesn't wait for model loading.
   - `POST /api/ask` (a sync `def`, so FastAPI runs it in its threadpool): rate-limit check → daily-cap check → `pipeline.answer([m.model_dump() for m in messages], answer_lang)` → return `{answer, citations, refused, refusal_reason, lang, span_id, snapshot_id, latency_ms}` (never `_chunks`). On `openai.RateLimitError` with code `insufficient_quota`, return 503 `{"error": "demo_quota"}`. On any other pipeline exception, log it and return 500 `{"error": "internal"}` without details.
   - `POST /api/feedback`: its own limiter → annotation via the Phoenix client (look up the exact method for span annotations in the installed `arize-phoenix-client`) → 204.
   - `GET /api/health` → `{status: "ok", index_version, snapshot_id}`.
   - 429 body `{"error": "rate_limited"}`; the UI shows a bilingual message for it and for `demo_quota`.
   - Mount `StaticFiles(directory=ROOT / "ui", html=True)` at `/`, **after** the API routes.
3. **`ui/index.html`** as specified. Layout:
   - header: title "UAE Gov Services Assistant · مساعد الخدمات الحكومية" and a GitHub link;
   - the disclaimer banner;
   - the example buttons row;
   - the chat log;
   - the input row: textarea, answer-language select, Send, New chat;
   - the privacy note;
   - footer: "Source snapshot: <date> · u.ae" (date from `/api/health`) and a link to the repo README.
   - It works at 360 px width.
   - Accessible: labelled controls, visible focus, buttons as `<button>`, `aria-live="polite"` on the chat log, contrast ≥ 4.5:1, system font stack with Arabic-capable fallbacks (`"Segoe UI", Tahoma, "Noto Sans Arabic", Arial, sans-serif`).
   - Thumbs: after a click both buttons disable; thumbs-down reveals an optional one-line comment box with "Send".
4. **Tests** (`tests/test_api.py`, FastAPI `TestClient`, with `pipeline.answer`, `load_index`, the warm-up and the Phoenix client monkeypatched):
   - health returns `index_version`;
   - ask returns the contract fields and no `_chunks`;
   - 422 for a 501-char question and for a last message with role `assistant`;
   - the 3rd request with the limit monkeypatched to 2 → 429;
   - the daily cap → 503 `demo_quota`;
   - a faked `insufficient_quota` error from `pipeline.answer` → 503 `demo_quota`; any other exception → 500 `internal`;
   - feedback with a bad `span_id` → 422; a valid one → 204, with the annotation call receiving the scrubbed comment;
   - `/` serves HTML that contains the disclaimer string.
5. **Manual check** with Phoenix up: run uvicorn, open http://localhost:8000. Do the layout, RTL, history and feedback checks on Ollama. Then restart with `LLM_BACKEND=openai` for one pass over the 4 examples only (~$0.005).
   - Click every example (the AR answer cites an EN page; the follow-up resolves; off-topic is refused).
   - Thumbs-down one answer with a comment → the annotation is visible on the trace in Phoenix.
   - Reload → history restored; New chat → cleared.
   - Arabic messages render right-to-left, English left-to-right.
   - Check at 360 px width in devtools.
   Show the owner.

## Files

Create: `src/arengov/api.py`, `ui/index.html`, `tests/test_api.py`. Change: `config.py`, `pyproject.toml`, `uv.lock`, `docs/HANDOFF.md`.

## Acceptance criteria

- `uv run pytest -m "not slow"` passes; ruff clean.
- The manual check passes, and the owner confirms the UI is understandable in under a minute.
- No `innerHTML` assignment with model or user text in `ui/index.html` (grep for `innerHTML`; only static templates allowed).

## Out of scope

No login, no server-side history, no streaming (D3, D45). Docker packaging and the ops report are phase 14; deployment is phase 16. The UI stays a single static file.

## What you should understand after this phase

- **A thin API over a pipeline:** validation at the trust boundary (pydantic), and why the endpoint is a sync `def` (blocking ML code runs in a threadpool instead of freezing the event loop).
- **Stateless server, stateful browser:** the client owns the conversation; the server can restart or scale without losing anything.
- **Cost guardrails for a public LLM demo:** rate limit per client, a global cap, input length limits.
- **XSS with LLM output:** treat model text like user input.
- **RTL/LTR mixing:** `dir="auto"` per message is what makes bilingual chat readable.
- **Feedback as trace annotations:** a thumbs-down is linked to the exact retrieval and prompt that produced the answer.

## Handoff checklist

- [ ] Acceptance criteria pass.
- [ ] HANDOFF: the manual check results, the Phoenix client method used for annotations, any UI rough edges left.
- [ ] Committed on `phase-13-api-ui`, pushed, PR open.
- [ ] Told the owner: merge when green, `/clear`, next is phase 14.
