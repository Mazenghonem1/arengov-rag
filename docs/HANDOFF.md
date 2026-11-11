# Handoff

Read at the start of every phase. At the end of each phase, **replace** the "Latest handoff" section with the new one (template below) and add one line to "History". Keep this file short. Details belong in commits and `docs/results.md`.

## Latest handoff

**Phase:** 01-crawl
**Date:** 2026-11-11
**Status:** done (owner accepted 145 EN / visa 29 as is; no backup category)

**Done**
- `crawl.py` (`normalize_url`, `category_of`, `mirror_url`, `page_id`, `crawl`, `diff`), CLI `crawl` / `diff`, `[01]` config constants, 7 tests (no network).
- Real crawl, snapshot `2026-11-11`: 307 requests, 1540 s, no abort, robots.txt = 404 (allow all), min gap between requests 3.16 s.

| category | EN | AR | AR missing |
|---|---|---|---|
| visa-and-emirates-id | 29 | 28 | 1 |
| jobs | 68 | 67 | 1 |
| business | 48 | 48 | 0 |
| **total** | **145** | **143** | 2 |

- `diff 2026-11-11 2026-11-11`: 0 new / 0 changed / 0 removed. Sampled raw files (jobs EN, business EN, visa AR) are real content pages.

**Deviations from plan**
- `raw_path` is relative to the snapshot dir (`raw/<sha1(url)>.html`).
- robots.txt is fetched first on every run (one logged request); a status other than 200/404 aborts.

**Metrics:** tests: 8 passed, ruff clean. **Acceptance misses:** EN pages 145 (< 150 target) and visa-and-emirates-id 29 (< 30). Visa and business exhausted their in-scope links (BFS queue empty at depth 3), so this is the site's structure, not the cap or depth limit.

**OpenAI spend:** $0 / $0

**Open issues**
- Decided 2026-11-11: accept 145 EN / 29 visa; `moving-to-the-uae` not added.
- 19 non-200 responses (all 404): robots.txt, 2 missing AR mirrors, 16 dead EN links. 8 of those are `.ashx` document links; `normalize_url` should also skip `.ashx` (not changed, crawl already done).
- TDRA: the automated reply (2026-11-10) gives no permission. Phases 15 (HF index upload) and 16 (public demo) are gated on a written answer. [YOU] follow-up sent: not yet.

**Notes for next phase**
- Snapshot id for phase 02: `2026-11-11` (`data/` is gitignored; rerun `crawl` locally on a fresh clone).
- Manifest order: each EN line is followed by its AR line.

**Commit:** see PR

## History

| Phase | Date | Result | Key metric |
|---|---|---|---|
| planning | 2026-11-09 | done | — |
| 00 setup | 2026-11-09 | done | CI green |
| 01 crawl | 2026-11-11 | done | 145 EN / 143 AR pages |

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
