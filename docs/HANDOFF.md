# Handoff

Read at the start of every phase. At the end of each phase, **replace** the "Latest handoff" section with the new one (template below) and add one line to "History". Keep this file short. Details belong in commits and `docs/results.md`.

## Latest handoff

**Phase:** 04-generate
**Date:** 2026-11-11
**Status:** done

**Done**
- `llm.py` (`LLMResult`, `complete`: one `openai` client, OpenAI or Ollama, judge role always OpenAI), `generate.py` (verbatim prompt, `build_prompt`, `parse_citations`, refusal, `generate`), `pipeline.answer`, CLI `ask "Q" [--lang] [--backend]`, `[04]` config constants.
- Tests: `test_llm.py`, `test_generate.py`, `test_pipeline.py` (no network).
- `REASONING_EFFORT = "none"`: `gpt-6-luna` accepted the first value tried.
- Judge probe: `gpt-6.1-terra` accepts `reasoning_effort="none"` and strict `json_schema` response_format. Both work, so phase 07 is unblocked.

**Deviations from plan**
- `__main__.main` reconfigures stdout to UTF-8 (the Windows cp1252 console crashed on Arabic output).
- `generate.py` has a file-level `noqa: E501` because the system prompt must stay verbatim.

**Metrics:** tests: 50 passed (1 deselected as slow), ruff clean.

Smoke tests (BM25 top-5):

| Backend | Question | Lang ok | Citations | Refused | Cost | Latency |
|---|---|---|---|---|---|---|
| ollama | How do I renew my Emirates ID? | yes | [1]-[4] valid | no | 0 | 140 s (cold model load) |
| ollama | What are the golden visa requirements? | yes | [1]-[5] valid | no | 0 | 14 s |
| ollama | تجديد الهوية الإماراتية | yes | [1],[5] valid | no | 0 | 16 s |
| ollama | ما هي شروط الإقامة الذهبية؟ | yes | [1],[4] valid | no | 0 | 16 s |
| ollama | best shawarma in Dubai | yes | 3 related links | yes (`no_answer`) | 0 | 10 s |
| openai | How do I renew my Emirates ID? | yes | [1] | no | $0.00012 | 6.9 s |
| openai | ما هي شروط الإقامة الذهبية؟ | yes | [1] | no | $0.00020 | 7.0 s |

Oddities: qwen3:8b leaves some sentences uncited, once leaked an English word "(holder)" into Arabic, and the golden-visa answer repeats [1]-[4] as separate entries for the same page. On the AR golden-visa question `gpt-6-luna` said the sources don't give detailed conditions and answered only partly, rather than `NO_ANSWER`; it only sees the top-5 BM25 chunks.

**Measured OpenAI cost per query:** ~$0.00016 (below the $0.001 flag, so the PLAN estimate holds).

**OpenAI spend:** ~$0.0005 / ~$0.0005 (effort probe, 2 smoke calls, 1 judge probe)

**Open issues**
- Citations for the same page are listed separately (one per chunk). Consider dedup by page in the UI (phase 13).
- Duplicate URLs for the same page (`Types-of-visas` vs `residence-visas`) can both appear in citations (from phase 03).
- TDRA: no written permission yet; phases 15-16 stay gated.

**Notes for next phase**
- Index version in use: `2026-11-11-v1`.
- Ollama's first call after idle is slow (~2 min for model load); later calls take 10-16 s.
- `ask` uses `LLM_BACKEND` from the environment; `--backend` overrides it.
- Phase 05 needs ~7 h of the owner's own time to write questions.

**Commit:** see PR

## History

| Phase | Date | Result | Key metric |
|---|---|---|---|
| planning | 2026-11-09 | done | — |
| 00 setup | 2026-11-09 | done | CI green |
| 01 crawl | 2026-11-11 | done | 145 EN / 143 AR pages |
| 02 clean-chunk | 2026-11-11 | done | 868 chunks (419 EN / 449 AR), max 400 tokens |
| 03 bm25 | 2026-11-11 | done | BM25 build 4.3 s, 41 tests |
| 04 generate | 2026-11-11 | done | ~$0.00016 / OpenAI query, 50 tests |
---

## Template (copy into "Latest handoff")

```
**Phase:** NN-name
**Date:** YYYY-MM-DD
**Status:** done | partial (Part A done, waiting on [YOU] …)

**Done**
- …

**Deviations from plan** (what changed vs the phase file, and why; contract changes also edited in PLAN.md)
- …

**Metrics** (copy the rows this phase added to docs/results.md; tests: N passed)
- …

**OpenAI spend** (this phase / cumulative vs the $5 credit; estimate in PLAN.md § Estimated OpenAI spend)
- $… / $…

**Open issues** (bugs, risks, anything left undone, with an owner)
- …

**Notes for next phase**
- … (facts the next session needs that aren't in the repo: index_version in use, τ value, model quirks, commands that were slow)

**Commit:** <short sha> <message>
```
