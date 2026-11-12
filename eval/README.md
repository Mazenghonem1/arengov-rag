# Writing the eval set

You write 60 questions in `eval/questions.jsonl`, one JSON object per line. Later phases are measured on them, so write them by reading real pages, not by asking an LLM.

## Workflow

1. `uv run python -m arengov sample-pages` prints 30 random EN pages (10 per category) with their EN and AR URLs. Re-run with `--seed 2` for more.
2. Open the pages in a browser. Read them (in EN or AR, see the mix rule below) and write questions a real expat would ask.
3. Find the gold `page_id` with `uv run python -m arengov search "your question"`. A `page_id` is the URL path without `/en/` or `/ar/`, lowercased, e.g. `information-and-services/visa-and-emirates-id/emirates-id`. The EN and AR versions of a page share one `page_id`.
4. Add the line to `questions.jsonl`. Number ids `q001`, `q002`, … Leave `split` out; Part B assigns it.
5. Run `uv run python -m arengov validate-eval` after every batch of about 10. It prints errors and a count table by type × lang.

## Target counts (validate with `--strict` at the end)

| type | ar | en | total |
|---|---|---|---|
| `single` (12 per category: visa-and-emirates-id, jobs, business; cover fees / eligibility / documents / steps / processing time) | 18 | 18 | 36 |
| `multi_turn` (2–3 turns) | 5 | 5 | 10 |
| `unanswerable_near` | 3 | 3 | 6 |
| `unanswerable_oos` | 2 | 2 | 4 |
| `mixed_script` | 2 | 2 | 4 |

## Fields

`id`, `lang` (`ar`/`en`: the language the answer should be in), `type`, `category` (`visa-and-emirates-id`/`jobs`/`business`), `turns` (list of user messages), `gold_page_ids`, `reference_answer`, `key_facts`, `answerable` (bool), `origin` (`human`/`llm_assisted`/`feedback`), `notes` (string, may be empty).

## Rules per type

- **single:** a question a real expat would ask, answerable from 1–3 pages. One turn.
- **multi_turn:** 2–3 turns. Turn 1 stands alone; later turns depend on it ("and for my wife?", "وكم الرسوم؟", "what are the fees?"). Gold pages are for the **last** turn.
- **unanswerable_near:** the topic exists on u.ae but the specific fact asked doesn't. Verify by searching and reading the page. `answerable: false`, gold/key facts empty, `reference_answer` `""`.
- **unanswerable_oos:** outside the three categories or not on u.ae (emirate-level fees, opinions, other countries). Same empty fields.
- **mixed_script:** an Arabic sentence with an English term, or the reverse. Turns must contain both Arabic and Latin letters. `lang` = the language you expect the answer in.

## Key facts and reference answer

- **key_facts:** 2–4 short atomic facts that must appear in a correct answer (a number, a document name, a condition), written in the question's language.
- **reference_answer:** 1–3 sentences in the question's language.
- No page text in the file, only page_ids, the short reference answer and key facts.

## Style rules

- Vary wording. Don't copy page headings into questions; that inflates BM25.
- Write about half of the AR questions about pages you first read in English, and vice versa.
- Mark `origin` honestly. If an LLM suggested the phrasing, use `llm_assisted`.

## EXAMPLES (invented page_ids; do not copy into questions.jsonl)

EXAMPLE single, EN:

```json
{"id": "q001", "lang": "en", "type": "single", "category": "visa-and-emirates-id", "turns": ["How long does an Emirates ID stay valid for a resident?"], "gold_page_ids": ["information-and-services/visa-and-emirates-id/example-page"], "reference_answer": "It is valid for the length of the residence visa, up to 10 years.", "key_facts": ["tied to residence visa", "up to 10 years"], "answerable": true, "origin": "human", "notes": ""}
```

EXAMPLE multi_turn, AR:

```json
{"id": "q002", "lang": "ar", "type": "multi_turn", "category": "jobs", "turns": ["كيف أحصل على تصريح عمل لموظف جديد؟", "وكم الرسوم؟"], "gold_page_ids": ["information-and-services/jobs/example-fees-page"], "reference_answer": "تبلغ الرسوم كذا درهم.", "key_facts": ["رسوم التصريح", "المبلغ بالدرهم"], "answerable": true, "origin": "human", "notes": "turn 2 needs turn 1"}
```

EXAMPLE unanswerable_near, EN:

```json
{"id": "q003", "lang": "en", "type": "unanswerable_near", "category": "business", "turns": ["What is the exact processing time in hours for a trade licence in Ajman?"], "gold_page_ids": [], "reference_answer": "", "key_facts": [], "answerable": false, "origin": "human", "notes": "page covers licences but gives no hours"}
```
