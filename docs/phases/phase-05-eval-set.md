# Phase 05: The evaluation set (Part A tooling → [YOU] write 60 questions → Part B validate)

**Size:** ~9 h total: Part A ~1.5 h, **[YOU] ~7 h writing**, Part B ~0.5 h · **Depends on:** phase 04 merged

This phase spans **two sessions**. Part A builds the tools, commits, opens the PR, and stops with HANDOFF status `partial`. The owner writes the questions offline. Part B starts in a new session on the same branch (`git switch phase-05-eval-set`) when the owner says the questions are written. Read HANDOFF to see which part is next.

## Goal

`eval/questions.jsonl` holds 60 hand-written, validated questions with gold pages, reference answers and key facts, split 40 dev / 20 test. Every later phase is measured on it.

## Decisions that apply

- The owner writes every question by reading real pages; a helper shows **randomly sampled pages stratified by category** (D32). An LLM may suggest phrasing only; such questions get `origin: "llm_assisted"`.
- Schema (D34) and type names: PLAN.md § Records. No page text in the file, only `page_id`s, short reference answers and key facts (D7).
- Composition (D33), exactly:

| type | ar | en | total |
|---|---|---|---|
| `single` (12 per category in total, covering fees / eligibility / documents / steps / processing time) | 18 | 18 | 36 |
| `multi_turn` (2–3 turns) | 5 | 5 | 10 |
| `unanswerable_near` | 3 | 3 | 6 |
| `unanswerable_oos` | 2 | 2 | 4 |
| `mixed_script` | 2 | 2 | 4 |

- Splits (D35): 40 dev / 20 test, stratified by type and language, assigned by a seeded script, never by hand.

## Part A tasks (Claude)

1. **`src/arengov/evalset.py`:**
   - `sample_pages(n=30, seed=1)`: distinct EN pages from the current index (one entry per `page_id`), n/3 per category, sampled with `random.Random(seed)`. Print a table: `page_id`, EN title, EN url, AR url (`pair_url` or "—").
   - `validate(path, strict=False) -> list[str]` returns error strings (empty = valid). Checks:
     - every line parses;
     - all fields present with the right types; `id` unique and matches `q\d{3}`;
     - `type`, `lang`, `category`, `origin` in their enums;
     - `answerable` is false exactly for the two unanswerable types;
     - answerable questions have 1–3 `gold_page_ids`, all existing in the current index, 2–4 `key_facts`, and a non-empty `reference_answer`;
     - unanswerable questions have empty gold, key facts and reference;
     - `turns` length is 1, except `multi_turn` which has 2–3;
     - `mixed_script` turns contain both Arabic and Latin letters;
     - `split` is in {dev, test} when present.
     - With `strict=True` also: exact counts per (type, lang) from the table above, 12 `single` questions per category, every question has a split, and the splits are 40/20.
   - `assign_splits(path, seed=13)`: sort questions by (type, lang, id), shuffle within each (type, lang) group with `random.Random(seed)`, concatenate the groups in sorted-key order, and put every 3rd question (index % 3 == 2) in `test` and the rest in `dev`. That's exactly 20 of 60. Rewrite the file in id order.
2. **CLI:** `sample-pages [--n 30] [--seed 1]`, `validate-eval [--strict]` (prints errors plus a count table by type × lang × split; exit 1 on errors), `assign-splits [--seed 13]`.
3. **`eval/README.md`**, the labeling guide for the owner:
   - The workflow: run `sample-pages`, read the pages in the browser, write questions in the file (one JSON object per line), run `validate-eval` often. Use `search` to find gold `page_id`s; a `page_id` is the URL path without `/en/` or `/ar/`, lowercased.
   - Rules per type:
     - `single`: a question a real expat would ask, answerable from 1–3 pages.
     - `multi_turn`: turn 1 standalone, later turns depend on it ("and for my wife?", "وكم الرسوم؟", "what are the fees?"); gold is for the **last** turn.
     - `unanswerable_near`: the topic exists on u.ae, but the specific fact asked doesn't (verify by searching).
     - `unanswerable_oos`: outside the 3 categories or not on u.ae (emirate-level fees, opinions, other countries).
     - `mixed_script`: an Arabic sentence with an English term, or vice versa; `lang` = the language the asker expects the answer in.
   - **Key facts:** 2–4 short atomic facts that must appear in a correct answer (a number, a document name, a condition), written in the question's language.
   - **Reference answer:** 1–3 sentences in the question's language.
   - Vary wording; don't copy page headings into questions (that inflates BM25).
   - Write about half of the AR questions about pages you first read in English, and vice versa.
   - Mark `origin` honestly.
   - Three example lines, clearly labelled EXAMPLE and kept only in the README (not in `questions.jsonl`): one `single` EN, one `multi_turn` AR, one `unanswerable_near` EN, with **invented** page_ids.
4. Create an empty `eval/questions.jsonl`.
5. **Tests** (`tests/test_evalset.py`): `validate` catches each kind of error on small synthetic files (monkeypatch the set of known page_ids); `assign_splits` on a synthetic 60-question file gives 40/20 and each (type, lang) group is split roughly 2:1 (test count = floor(g/3) or ceil(g/3)).
6. Commit, push, open the PR (note "Part A; Part B pending"). HANDOFF status `partial: Part A done, waiting on [YOU] questions`. Tell the owner what to do next (below) and stop.

## [YOU] task: write the 60 questions (~7 h)

Follow `eval/README.md`. Work in batches of 10, running `validate-eval` after each. Leave `split` out; Part B assigns it. When `validate-eval` shows no errors and the counts match the table, start a new session and say "phase 05 Part B".

## Part B tasks (Claude, new session)

1. `git switch phase-05-eval-set && git pull`.
2. `validate-eval`, fix trivia with the owner (typos in page_ids, counts).
3. `assign-splits`, then `validate-eval --strict` must pass. Show the count table.
4. Spot-check 5 random answerable questions: run `search` with the question and show whether a gold page appears in the top 10. This only previews, it isn't a metric; it catches wrong gold labels early. Fix labels with the owner if one is clearly wrong.
5. Commit `eval/questions.jsonl`, push, update the PR body, HANDOFF status `done`.

## Files

Create: `src/arengov/evalset.py`, `tests/test_evalset.py`, `eval/README.md`, `eval/questions.jsonl`. Change: `__main__.py`, `docs/HANDOFF.md`.

## Acceptance criteria

- `uv run pytest -m "not slow"` passes; ruff clean.
- `uv run python -m arengov validate-eval --strict` exits 0: 60 questions, counts as in the table, 40 dev / 20 test.

## Out of scope

Metrics and eval runs are phases 06–07. Questions are written by the owner; Claude's role on them is limited to validation, formatting fixes and pointing out likely label errors for the owner to decide.

## What you should understand after this phase

- **Why a hand-labeled set matters:** you can't improve what you don't measure, and LLM-generated questions are biased toward the model's own phrasing.
- **Question types as failure probes:** near-miss unanswerables test hallucination, multi-turn tests rewriting, mixed-script tests tokenization and language detection.
- **Page-level gold labels** and why they make cross-lingual scoring fair (either language version counts).
- **Dev vs test:** tune on dev, report test. 20 test questions means 1 question = 5 points, so small differences are noise.
- **Stratified, seeded splits:** reproducible, and every type/language appears in both splits.

## Handoff checklist

- [ ] Part A: tools + guide committed, PR open, HANDOFF `partial`, owner told what to do.
- [ ] Part B: `validate-eval --strict` passes; questions committed; HANDOFF `done` with the count table and spot-check results.
- [ ] Told the owner: merge when green, `/clear`, next is phase 06.
