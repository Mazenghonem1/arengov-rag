# Phase 07: Answer evaluation, LLM judge, baseline and thresholds

**Size:** ~4 h · **Depends on:** phase 06 merged · **Cost:** ~$1 of OpenAI

## Goal

`uv run python -m arengov eval-answers` runs the full pipeline on eval questions, scores answers with deterministic checks and an LLM judge, records the **answer baseline** for the BM25 pipeline, and `eval/thresholds.json` holds the first CI gates.

## Decisions that apply

- **Deterministic checks** (code, D36):
  - `refusal_correct` = `refused == (not answerable)`, over all questions.
  - `lang_match` = `detect_lang(answer without [n] markers and URLs) == question.lang`, over all questions, refusals included.
  - `citation_valid` = ≥1 citation and no invalid markers, over answered (non-refused) questions.
- **Judge** (D28, D36): `gpt-5.6-terra` (`role="judge"`), one call per answer, structured JSON with a reason and a pass/fail for `faithfulness`, `correctness`, `citation_accuracy`. It runs only on **answerable questions that were answered**.
- Multi-turn: until phase 10, `pipeline.answer` sees all user turns but uses only the last (D58). The eval passes the turns as user messages.
- Language: the eval calls `answer(messages, answer_lang="auto")` so detection is tested too.
- Ops metrics per run: `latency_p50_ms`, `latency_p95_ms`, `cost_per_q_usd` (generation cost only; judge cost reported separately as `eval_cost_usd`).
- **Thresholds** (D37), on the **test** split: `threshold = floor((baseline*100 - 5) / 5) * 5 / 100`. Gated: `recall@5`, `mrr@10` (retrieval) and `refusal_correct`, `lang_match`, `faithfulness`, `citation_accuracy` (answers). Ratchet: `set-thresholds` never lowers an existing value.

## Tasks

1. Add `JUDGE_MAX_TOKENS = 800` to `config.py`.
2. **`src/arengov/judge.py`:**
   - `JUDGE_SYSTEM` (exact text):
     ```
     You grade one answer from a question-answering system about UAE government services.
     You get the user's question, the numbered sources the system was given, the system's answer, a reference answer and key facts written by a human expert.
     Grade three criteria, each strictly pass or fail:
     - faithfulness: pass if every factual statement in the answer is supported by the numbered sources. Fail if any statement is unsupported by them, even if it is true in the real world.
     - correctness: pass if the answer contains every key fact (any wording, any language) and nothing in it contradicts the reference answer. Fail otherwise.
     - citation_accuracy: pass if every bracketed citation [n] points to a source that supports the sentence it is attached to. Fail if any citation points to a source that does not support its sentence.
     Answers and sources may be in Arabic or English; judge meaning, not language.
     For each criterion write a one-sentence reason first, then the verdict.
     ```
   - `JUDGE_SCHEMA`: an object with required keys `faithfulness`, `correctness`, `citation_accuracy`, each `{"reason": string, "pass": boolean}` with `additionalProperties: false` at every level (strict mode requires it).
   - `judge(question, chunks, answer, reference_answer, key_facts, earlier_turns=())` builds the user message:
     ```
     Earlier user messages: <only if any, joined by " | ">
     Question: …
     Sources:
     [1] (lang) title - url
     <text>
     …
     Answer:
     …
     Reference answer:
     …
     Key facts:
     - …
     ```
     It calls `complete(JUDGE_SYSTEM, [msg], JUDGE_MAX_TOKENS, role="judge", json_schema=JUDGE_SCHEMA)`, and returns the parsed dict plus `"cost_usd"`.
3. **`pipeline.answer`:** also return the final chunk dicts under the key `"_chunks"` (the leading underscore marks it internal; the API strips it in phase 13). The judge needs exactly what the generator saw. (`_chunks` is already listed in PLAN.md § `pipeline.answer` returns.)
4. **`src/arengov/eval_answers.py`:**
   - `run(split, *, backend=None, label, record=False)`: set `config.LLM_BACKEND` if `backend` is given. For each question in the split (all types):
     - `out = pipeline.answer([{"role": "user", "content": t} for t in q["turns"]], "auto")`;
     - deterministic checks;
     - the judge when answerable and not refused.
   - Keep going on errors: log them, count them in the summary as `errors`, and treat that question as failing every check.
   - Summary `{kind: "answers", label, split, index_version, git_sha, timestamp, backend, gen_model, n, n_judged, errors, metrics: {...}, by_lang, by_type, eval_cost_usd}`. Write it plus per-question details (answer, citations, refused, checks, judge reasons, latency, cost) as in phase 06. `--record` appends a row to `docs/results.md` (answer columns filled, retrieval columns `—`). `--out PATH` copies the summary.
   - Print the summary table and the ids of failed checks per metric.
   - `rejudge(details_path)` re-runs only the judge on stored outputs (used in phase 11). It needs the stored chunk texts: the details lines keep `final_chunk_ids`, and `rejudge` re-reads the texts from the index of the same `index_version`.
5. **Thresholds:**
   - `set-thresholds RETRIEVAL_SUMMARY ANSWERS_SUMMARY`: both must be test-split summaries. Compute per the rule above, ratchet against the existing `eval/thresholds.json` (`{"split": "test", "retrieval": {...}, "answers": {...}}`), write it, and print old → new.
   - `check-thresholds SUMMARY [SUMMARY…]`: compare each gated metric present in the summaries; print a pass/fail table; exit 1 if any value is below its threshold.
6. **CLI:** `eval-answers --split dev|test|all --label NAME [--backend openai|ollama] [--record] [--out PATH] [--rejudge DETAILS]`, `set-thresholds`, `check-thresholds`.
7. **Tests** (`tests/test_eval_answers.py`, `tests/test_judge.py`, `tests/test_thresholds.py`):
   - deterministic checks on fake outputs (refused/answerable combos, `lang_match` with `[n]` and URLs in the text, invalid citations);
   - the judge message format and parsing with `complete` faked to return schema-valid JSON;
   - the threshold rule: 0.734 → 0.65, 0.70 → 0.65, 1.0 → 0.95, 0.04 → 0.0;
   - the ratchet keeps a higher old value;
   - `check-thresholds` exits 1 on one failure and 0 when all pass.
8. **Baseline runs** (with `--record`): `eval-answers --split dev --label bm25-baseline`, then `--split test --label bm25-baseline` (~$0.7 total). Then `set-thresholds <phase-06 bm25-baseline test retrieval summary> <today's test answers summary>`, and `check-thresholds` on both (must pass).
9. **Read the failures:** for dev, list each judge-failed or refusal-failed question with the judge's reason and a one-line cause guess (retrieval miss, hallucination, language drift, over-refusal). Put the top 5 in HANDOFF.

## Files

Create: `src/arengov/judge.py`, `src/arengov/eval_answers.py`, `tests/test_eval_answers.py`, `tests/test_judge.py`, `tests/test_thresholds.py`, `eval/thresholds.json`, `eval/results/*.json` (2 summaries). Change: `pipeline.py`, `config.py`, `__main__.py`, `docs/results.md`, `docs/HANDOFF.md`.

## Acceptance criteria

- `uv run pytest -m "not slow"` passes; ruff clean.
- Two answer rows in `docs/results.md`; `eval/thresholds.json` committed; `check-thresholds` passes on the test summaries.
- `eval_cost_usd` of the test run ≤ $0.60 (printed).

## Out of scope

The judge is used as-is here; validating it against the owner's grades is phase 11. It runs only on stored outputs, never in the request path. Pipeline improvements start in phase 08.

## What you should understand after this phase

- **Two kinds of checks:** deterministic (cheap, exact, can't disagree with themselves) vs judged (semantic, costs money, must be validated). Use code wherever code can decide.
- **The three judge criteria are different failures:**
  - unfaithful = the model added something not in the sources;
  - incorrect = it missed or contradicted the facts;
  - bad citation = the right facts attributed to the wrong source.
- **Reason-then-verdict** and **strict JSON schemas:** why both make an LLM judge more reliable and parseable.
- **Regression thresholds as a ratchet:** a gate stops quality from silently dropping; the 5-point margin absorbs noise from a 20-question test set.
- **Cost of evaluation:** what a full run costs and why CI runs the answer eval only when generation code changes.

## Handoff checklist

- [ ] Acceptance criteria pass.
- [ ] HANDOFF: the answer baseline rows, the thresholds, the top-5 failure analysis, the eval cost.
- [ ] Committed on `phase-07-answer-eval`, pushed, PR open.
- [ ] Told the owner: merge when green, `/clear`, next is phase 08.
