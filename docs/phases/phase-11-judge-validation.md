# Phase 11: Validate the LLM judge against your own grades (Part A → [YOU] grade → Part B)

**Size:** ~4.5 h total: Part A ~1 h, **[YOU] ~2.5 h grading**, Part B ~1 h · **Depends on:** phase 10 merged · **Cost:** ~$0.45, ≤ $0.90 if the prompt is revised (terra judge, D63)

This phase spans **two sessions**, like phase 05. Part A exports a blind grading sheet and stops (HANDOFF `partial`). The owner grades offline. Part B (a new session on the same branch) computes agreement.

## Goal

The README can state "the LLM judge agrees with human grades X% of the time (Cohen's κ = Y)" per criterion, measured on blind grades of the latest dev+test answers.

## Decisions that apply

- **The judge being validated is `gpt-5.6-terra`** (D63), the judge behind the README's headline numbers. Development runs were judged by luna, so Part A first re-judges phase 10's stored answers with terra; the owner's grades are compared against terra's verdicts.
- The owner blind-grades **all answered answerable responses** (dev + test, ~45) from the latest answer runs (phase 10's `rewrite` dev and test details) on the 3 judge criteria, pass/fail, **without seeing the judge's verdicts** (D38).
- Report per criterion: n, agreement %, Cohen's κ, and the confusion counts (judge × human).
- Target: ≥ 85% agreement and κ ≥ 0.6. If a criterion misses: revise `JUDGE_SYSTEM` using **dev disagreements only**, re-judge the same stored answers once (`eval-answers --rejudge … --judge-model gpt-5.6-terra`), and report before/after numbers plus the **test-only** agreement after the revision (the held-out check). Revise at most once (D38).
- Grading files contain generated answers derived from the corpus, so they live in gitignored `eval/grading/` (D7, D57). Only the numbers and question ids are committed.
- Cohen's κ: `po` = observed agreement; `pe = p_yes_judge * p_yes_human + p_no_judge * p_no_human`; `κ = (po - pe) / (1 - pe)`. When `pe == 1`, report κ as `null` ("undefined: all same label").

## Part A tasks (Claude)

0. **Re-judge with terra:** `eval-answers --rejudge <phase-10 rewrite dev details> --judge-model gpt-5.6-terra --record` and the same for the test details (~$0.45). These terra-judged details are the input to everything below. Note the spend in HANDOFF.
1. **`judge.export_blind(details_paths, out_dir="eval/grading", seed=7)`:**
   - collect every line where `answerable and not refused`;
   - shuffle with the seed and assign `item_id` 1…n;
   - write `items.md`: per item a heading `## Item <item_id>`, then the question (and earlier turns), the numbered sources exactly as the generator saw them, the answer, the reference answer and the key facts, with **no judge output**;
   - write `grades.csv` with columns `item_id,faithfulness,correctness,citation_accuracy,note` (empty cells);
   - write `key.json` mapping `item_id` → `{q_id, split, details_path, judge: {criterion: bool}}`.
   - The rubric the owner follows is printed at the top of `items.md`: the three criteria definitions from `JUDGE_SYSTEM`, word for word.
2. **CLI:** `judge-export DETAILS [DETAILS…]`.
3. Run it on the **terra-rejudged** dev and test details from task 0, and print n.
4. **Tests:** `export_blind` on 3 fake detail lines: refused and unanswerable lines excluded, no judge verdict text in `items.md`, ids consistent between `grades.csv` and `key.json`.
5. Commit (code only), push, open the PR, HANDOFF `partial: Part A done, waiting on [YOU] grading`. Give the owner the instructions below, then stop.

## [YOU] task: grade (~2.5 h)

Open `eval/grading/items.md` next to `eval/grading/grades.csv`. For each item enter `1` (pass) or `0` (fail) for each criterion, using the rubric at the top. Judge only what's on the page: don't look up u.ae, and don't open the eval details files (they contain the judge's verdicts). Add a short note when unsure. When every row is filled, start a new session and say "phase 11 Part B".

## Part B tasks (Claude, new session)

1. `git switch phase-11-judge-validation && git pull`.
2. **`judge.agreement(grades_csv, key_json)`** → per criterion `{n, agreement, kappa, confusion: {jp_hp, jp_hf, jf_hp, jf_hf}, disagreements: [q_ids]}`, also split by dev/test. Validate that every row is filled with 0/1 and report any missing rows.
3. **CLI:** `judge-agreement [--grades eval/grading/grades.csv] [--key eval/grading/key.json] [--label NAME] [--record]` writes `eval/results/<ts>_judge-agreement_<label>.json`. With `--record` it appends to a second table in `docs/results.md` titled "Judge validation": `| date | label | criterion | n | agreement | κ | judge pass / human pass |`.
4. Run it with `--label v1 --record`.
5. If every criterion meets the target, you're done. Otherwise:
   - read the dev disagreements (judge reason vs the owner's grade and note), summarize the pattern for the owner, and propose a revised `JUDGE_SYSTEM` (smallest change that addresses the pattern). The owner approves.
   - `eval-answers --rejudge <dev details> --judge-model gpt-5.6-terra` and the same for `<test details>`, which write new details/summaries with a `-rejudge-…` label suffix (~$0.45).
   - Update `key.json`'s judge verdicts from the re-judged details (a small helper, or `judge-agreement --rejudged DETAILS…`), then run `judge-agreement --label v2 --record`.
   - Report v1 vs v2, and v2 on **test only**.
6. **Tests:** κ on the textbook example (50 items: both yes 20, judge yes/human no 5, judge no/human yes 10, both no 15 → po = 0.70, pe = 0.50, κ = 0.40); `pe == 1` → `null`; agreement %.
7. Commit, push, update the PR, HANDOFF `done`.

## Files

Change: `src/arengov/judge.py`, `src/arengov/eval_answers.py` (rejudge output naming, if needed), `__main__.py`, `docs/results.md`, `docs/HANDOFF.md`. Create: `tests/test_judge_agreement.py`, `eval/results/*_judge-agreement_*.json`. Never committed: `eval/grading/*`.

## Acceptance criteria

- `uv run pytest -m "not slow"` passes (including the κ = 0.40 example); ruff clean.
- A "Judge validation" table exists in `docs/results.md` with agreement and κ per criterion (and v2 rows if a revision happened).
- `git status` shows nothing under `eval/grading/` staged.

## Out of scope

The owner's grades are the ground truth for this phase. The judge prompt is revised once at most, using dev items, so the test agreement stays an honest held-out number. Judge validation doesn't change the generation pipeline.

## What you should understand after this phase

- **Why validate a judge at all:** an unvalidated LLM judge is an opinion; agreement with a human makes it a measurement.
- **Agreement % vs Cohen's κ:** if 90% of answers pass, a judge that always says "pass" scores 90% agreement; κ subtracts chance agreement and exposes that.
- **Blind grading and anchoring:** seeing the judge's verdict first biases you toward it.
- **Overfitting the judge prompt:** revising on dev and reporting test is the same discipline as tuning a model.
- **Which criterion is hardest to judge** (often citation accuracy) and why.

## Handoff checklist

- [ ] Part A: export done, PR open, HANDOFF `partial`, owner instructed.
- [ ] Part B: acceptance criteria pass; HANDOFF has the agreement table (and revision notes).
- [ ] Told the owner: merge when green, `/clear`, next is phase 12 (**Docker Desktop must be installed**).
