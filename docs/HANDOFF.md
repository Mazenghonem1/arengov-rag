# Handoff

Read at the start of every phase. At the end of each phase, **replace** the "Latest handoff" section with the new one (template below) and add one line to "History". Keep this file short. Details belong in commits and `docs/results.md`.

## Latest handoff

**Phase:** 02-clean-chunk
**Date:** 2026-11-11
**Status:** done (owner approved one cleaned page per language and 6 random chunks)

**Done**
- `clean.py` (`clean_html`), `chunk.py` (`count_tokens`, `chunk_page`), `index.py` (`build_index`, `Index`, `load_index`), CLI `build-index`, `[02]` config constants, synthetic EN/AR fixtures, 9 new tests (1 slow).
- Real build: `data/index/2026-11-11-v1/`; `eval/index_version.txt` = `2026-11-11-v1`.
- Selectors: `CONTENT_SELECTOR = main#mainContentContainer` (present on all 288 pages). Dropped: script, style, noscript, svg, iframe, ins, form, select, button, `.topic-navigation`, `.artical-info-link`.

**Deviations from plan**
- u.ae pages have no `h1` (title is in a hero header outside `main`), so the title always comes from `<title>` minus the site suffix.
- Text outside `h1-h4, p, li, table` is 6.0% of the container's visible text (<10%), so no tags were added. Not captured: `h6` titles and link-card text on landing pages, which are skipped anyway.

**Metrics:** tests: 16 passed, ruff clean.

| | EN | AR |
|---|---|---|
| pages kept | 113 | 110 |
| pages skipped (<200 chars, link-list landing pages) | 32 | 33 |
| chunks | 419 | 449 |

Chunks per category: visa-and-emirates-id 119, jobs 464, business 285. Tokens (bge-m3): mean 228.1, max 400.

**OpenAI spend:** $0 / $0

**Open issues**
- `normalize_url` still doesn't skip `.ashx` (not needed here).
- TDRA: no written permission yet; phases 15-16 stay gated.
- Link-only sections ("Related digital services") make tiny, weak chunks; revisit only if phase 06 recall shows a problem.

**Notes for next phase**
- Index version in use: `2026-11-11-v1` (local only, `data/` is gitignored; rebuild with `build-index` on a fresh clone).
- `build-index` downloads the bge-m3 tokenizer from Hugging Face on first run.
- H4 headings stay as `#### ` lines inside chunk text.

**Commit:** see PR

## History

| Phase | Date | Result | Key metric |
|---|---|---|---|
| planning | 2026-11-09 | done | — |
| 00 setup | 2026-11-09 | done | CI green |
| 01 crawl | 2026-11-11 | done | 145 EN / 143 AR pages |
| 02 clean-chunk | 2026-11-11 | done | 868 chunks (419 EN / 449 AR), max 400 tokens |

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
