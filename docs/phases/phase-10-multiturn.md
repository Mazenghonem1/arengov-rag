# Phase 10: Multi-turn follow-ups via query rewriting, and demo examples

**Size:** ~2.5 h · **Depends on:** phase 09 merged · **Cost:** ~$0.20 (luna-judged dev + test answer evals, rewrites, demo checks)

## Goal

Follow-up questions ("and for my wife?", "وماذا عن تجديدها؟") are rewritten into standalone queries before retrieval, multi-turn eval questions measure that, τ is re-picked with them included, and the 4 demo examples are chosen and saved for the UI.

## Decisions that apply

- Chat history lives in the browser; the server is stateless (D3). Every request sends the conversation.
- **Rewriter input** (D58): the previous ≤ `HISTORY_MAX_TURNS = 3` **user** messages + the new one; assistant messages are ignored. It runs only when there is at least one previous user message. Output in the follow-up's language.
- After rewriting, everything is single-turn: retrieval and generation use the rewritten query (D58).
- Answer language is detected from the **original** last message, not the rewritten one.
- Retrieval eval rewrites multi-turn questions via the LLM (~$0.002 per run), so `eval-retrieval` now needs `OPENAI_API_KEY` (D58). `eval-retrieval` and `pick-tau` get a `--backend openai|ollama` flag **defaulting to `openai`**, set for the whole run, so a local `LLM_BACKEND=ollama` never leaks into recorded metrics (D67).
- Debug the rewriter ad hoc on Ollama (`LLM_BACKEND=ollama`, free). OpenAI is used for the recorded runs in task 7 and the demo checks in task 9, because the demo runs on OpenAI.
- Demo beats (D2, D31c): an English question; an Arabic question whose cited source is really English; an Arabic follow-up to it; an off-topic question that gets refused.

## Tasks

1. Add the `[10]` constants to `config.py`.
2. **`src/arengov/rewrite.py`:**
   - `REWRITE_SYSTEM` (exact text):
     ```
     You rewrite a follow-up question into one standalone question for a search engine about UAE government services.
     Use the earlier questions only to resolve references such as "it", "that visa" or "and for my wife?".
     Keep the language of the follow-up question. Keep names of visas, permits and documents exactly as written.
     If the follow-up is already standalone, return it unchanged.
     Reply with the standalone question only.
     ```
   - The user message: `Earlier questions:\n1. …\n2. …\nFollow-up question: …`.
   - `rewrite(prev_user_msgs, question, lang)` calls `complete(..., REWRITE_MAX_TOKENS)` and returns `(text.strip(), LLMResult)`. If the result is empty, fall back to `question`.
3. **`pipeline.answer`:**
   - `user_msgs` = contents of `role == "user"` messages; `question = user_msgs[-1]`; `prev = user_msgs[:-1][-HISTORY_MAX_TURNS:]`.
   - Detect `lang` from `question`.
   - `rewritten = rewrite(prev, question, lang)[0] if prev else question`.
   - Retrieve and generate with `rewritten`; return it as `rewritten_query`; add the rewrite tokens and cost to `usage`.
4. **`eval_retrieval.run`:** add the `backend="openai"` parameter (and the `--backend` CLI flag) and set `config.LLM_BACKEND` for the run. For `multi_turn` questions the query is `rewrite(turns[:-1][-3:], turns[-1], q["lang"])[0]`; store it in details. Give `pick-tau` the same `--backend` flag. `eval_answers` needs no change (it already sends all turns and defaults to `openai`).
5. **Re-pick τ:** extend `pick_tau` to include `multi_turn` questions (with rewriting), run it on dev, apply the safety rule, and update `GATE_TAU`.
6. **Tests** (`tests/test_rewrite.py`, additions to `tests/test_pipeline.py`):
   - the prompt includes only user messages, at most 3 previous ones;
   - empty model output → original question;
   - `pipeline.answer` with one message doesn't call `rewrite`; with history it does, and retrieval receives the rewritten text;
   - `lang` comes from the original question.
7. **Eval runs** (`--record`):
   - `eval-retrieval --split test --label rewrite`
   - `eval-retrieval --split dev --label rewrite`
   - `eval-answers --split dev --label rewrite` (luna judge)
   - `eval-answers --split test --label rewrite` (luna judge; phase 17 re-judges these stored test answers with terra for the README, so keep `eval/results/details/` on disk)
   Compare the `multi_turn` row of `by_type` with phase 09 and put both numbers in HANDOFF.
8. **Ratchet thresholds**; `check-thresholds` passes.
9. **Choose the demo examples.** From the latest dev+test answer details, list candidates:
   - (a) an EN `single` with all judge checks passing;
   - (b) an AR question, answered and judge-passing, whose citations include an `en` page. If there's none, search for AR questions about pages whose AR mirror is missing (`pair_url` null) and test 3–5 with `ask --backend openai`;
   - (c) a 2-turn AR conversation starting from (b)'s question whose follow-up works with `ask`-style multi-message input. Test it via a small Python call to `pipeline.answer` with two user messages and `config.LLM_BACKEND = "openai"`;
   - (d) an `unanswerable_oos` question that gets refused.
   Show 2 candidates per slot to the owner and **let the owner pick**. Write `ui/examples.json`:
   ```json
   [
     {"id": "en", "label": "English question", "messages": ["…"]},
     {"id": "ar", "label": "سؤال بالعربية", "messages": ["…"]},
     {"id": "ar_followup", "label": "متابعة", "messages": ["<the follow-up only>"], "after": "ar"},
     {"id": "offtopic", "label": "Off-topic question", "messages": ["…"]}
   ]
   ```

## Files

Create: `src/arengov/rewrite.py`, `tests/test_rewrite.py`, `ui/examples.json`. Change: `pipeline.py`, `eval_retrieval.py`, `config.py`, `tests/test_pipeline.py`, `eval/thresholds.json`, `docs/results.md`, `docs/HANDOFF.md`.

## Acceptance criteria

- `uv run pytest -m "not slow"` passes; ruff clean.
- 4 new rows in `docs/results.md`; multi-turn recall@5 on test ≥ its phase 09 value. If it's lower, investigate rewrite outputs in the details before finishing.
- `GATE_TAU` re-picked; `check-thresholds` passes.
- `ui/examples.json` holds the owner-approved examples, and each one behaves as intended when run.

## Out of scope

Assistant messages stay out of the rewriter and the generator (D58). History is limited to 3 previous user turns. The UI that shows the examples is phase 13.

## What you should understand after this phase

- **Conversational query rewriting** (sometimes called "condense question"): a stateless retriever can't resolve "it". One cheap LLM call turns a follow-up into a search query, and everything downstream stays single-turn.
- **Why only user messages:** they carry the intent; assistant answers are long, add noise and cost, and make eval replay depend on earlier answers.
- **Re-tuning after a change:** τ was picked before rewriting existed, and a pipeline change can invalidate earlier tuned values.
- **Choosing a demo from data:** demo examples come from eval results, not luck, and the cross-lingual one is checked to really cite an English page.

## Handoff checklist

- [ ] Acceptance criteria pass.
- [ ] HANDOFF: multi-turn before/after, the new τ, the chosen demo examples (ids + text), the new thresholds.
- [ ] Committed on `phase-10-multiturn`, pushed, PR open.
- [ ] Told the owner: merge when green, `/clear`, next is phase 11. **Phase 11 needs ~2.5 h of your own grading time.**
