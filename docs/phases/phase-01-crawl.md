# Phase 01: Polite crawler and dated snapshot

**Size:** ~3 h (of which ~25 min is the real crawl running in the background) · **Depends on:** phase 00 merged

## Goal

`uv run python -m arengov crawl` politely fetches ~200 English u.ae pages from 3 categories plus their Arabic mirrors into `data/snapshots/<YYYY-MM-DD>/` with a manifest, and `diff` compares two snapshots.

## Prerequisites

- Phase 00 merged. `httpx` installed.
- Facts checked 2026-11-09: u.ae serves server-rendered HTML; `https://u.ae/robots.txt` and `/sitemap.xml` return 404; the Arabic page is the same path with `/ar/` instead of `/en/`; category pages are `https://u.ae/en/information-and-services/<category>` with sub-pages below them.

## Decisions that apply

- Categories: `visa-and-emirates-id`, `jobs`, `business` (D8). BFS from each category page, depth ≤ 4, staying inside `/en/information-and-services/<category>` (D9). **Cap 70 successfully fetched EN pages per category** (D60c).
- Politeness (D10): single-threaded; sleep `CRAWL_DELAY_S = 3.0` before **every** request; `User-Agent` = `config.USER_AGENT`; abort after 3 **consecutive** errors (HTTP 403, 429, ≥500, or network exception); already-fetched URLs are never re-requested; every request is logged.
- Respect robots.txt if it exists by the time you crawl: fetch it first and use `urllib.robotparser`; a 404 means allow all.
- Snapshot layout and manifest fields: see PLAN.md § Paths and § Records (D11). `snapshot_id` = crawl start date.
- `page_id` = path without `/en` or `/ar`, lowercased, no trailing slash. URLs deduplicated case-insensitively (D60d). AR mirror: fetch it; 404 means `pair_url = null` (D18).
- Refresh is manual: `crawl` again on a later date gives a new folder, and `diff` reports new/changed/removed pages (D12).

## Tasks

1. `uv add beautifulsoup4 lxml`.
2. Add the `[01]` constants from PLAN.md § Config constants to `config.py`.
3. **`src/arengov/crawl.py`** with the functions in PLAN.md § Modules:
   - `normalize_url(href, base)`: resolve relative links against `base`; accept only host `u.ae` or `www.u.ae` (rewrite to `https://u.ae`); drop query and fragment; drop trailing slash; return `None` for other hosts, `mailto:`, `tel:`, `javascript:`, and file links (`.pdf`, `.jpg`, `.png`, `.docx`, `.xlsx`, `.zip`).
   - `category_of(url)`: the category if the path, case-insensitively, equals or starts with `/en/information-and-services/<category>/` for one of `CATEGORIES`; else `None`.
   - `mirror_url(url)`: swap the first path segment `/en/` ↔ `/ar/`.
   - `page_id(url)`: as defined above.
   - `crawl(snapshot_id, client=None)`:
     - Create `SNAPSHOT_ROOT/<id>/raw/`. Load `manifest.jsonl` if it exists (resume). A URL already in the manifest is read from its raw file instead of fetched.
     - For each category in order: BFS queue starting at the category URL, depth 0. Pop a URL; skip if visited (lowercased key). Fetch it (or read from cache). Count it against the cap if the status is 200 and the content type is HTML. Store it. Extract `<a href>` links → `normalize_url` → keep those with the same `category_of` and depth+1 ≤ 4 → enqueue. Then fetch its AR mirror, store it with `lang="ar"`, and set both records' `pair_url`s (or `null` on 404). Links on AR pages are not followed.
     - Store: write raw bytes to `raw/<sha1(url)>.html`; append the manifest line (fields per PLAN.md; `title` = `<title>` text stripped; `depth`; `sha256` of the bytes). Since `pair_url` is known only after the mirror fetch, write the EN line after the mirror is done.
     - Non-200 responses: log them, write no raw file and no manifest line. 404 doesn't count as an error.
     - A module-level `_sleep = time.sleep` called before each network request, so tests can patch it.
     - `client` defaults to `httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=CRAWL_TIMEOUT_S, follow_redirects=True)`. If a redirect lands outside the category, treat the page as skipped.
     - On abort, raise `RuntimeError` with the last 3 statuses. The manifest written so far stays (resume works).
     - At the end, print a summary: EN/AR pages per category, AR mirrors missing, total requests, elapsed time.
   - `diff(old_dir, new_dir)`: compare manifests by `url` and `sha256`; return `{"new": [...], "changed": [...], "removed": [...]}`.
   - `crawl.log`: one line per request: `ISO-time<TAB>status<TAB>elapsed_ms<TAB>url`.
4. **CLI:** `crawl [--snapshot-id YYYY-MM-DD]` (default: today's date) and `diff OLD_ID NEW_ID` (prints counts, then the URL lists).
5. **Tests** (`tests/test_crawl.py`, no network). Use `httpx.Client(transport=httpx.MockTransport(handler))` with a fake site of synthetic pages: one category page linking to two sub-pages, one out-of-category link, one external link, and a page at depth 5. Patch `crawl._sleep` and monkeypatch `config.CRAWL_MAX_EN_PER_CATEGORY` and `CATEGORIES` where needed. Cover:
   - `normalize_url`: relative, fragment, query, trailing slash, `www.u.ae`, other host, `.pdf`.
   - `page_id` and `mirror_url`.
   - BFS stays in scope and within the depth limit; the per-category cap is respected.
   - AR mirror stored and `pair_url` set both ways; mirror 404 → `pair_url` null.
   - 3 consecutive 503s → `RuntimeError`; manifest kept.
   - A resume run makes zero network requests for already-fetched URLs.
   - `diff` finds new, changed and removed pages.
6. **Real crawl.** Run `uv run python -m arengov crawl` in the background (~400 requests × 3 s ≈ 20–25 min). When it finishes, show the summary to the owner.
7. Sanity check: open 3 random raw files (one per category, one AR) and confirm they're real content pages, not error pages.

## Files

Create: `src/arengov/crawl.py`, `tests/test_crawl.py`. Change: `src/arengov/config.py`, `src/arengov/__main__.py`, `pyproject.toml`, `uv.lock`, `docs/HANDOFF.md`.

## Acceptance criteria

- `uv run pytest -m "not slow"` passes; ruff clean.
- The real crawl finished without an abort. `manifest.jsonl` has ≥150 EN lines with status 200, every category has ≥30 EN pages, and every line has all manifest fields.
- `crawl.log` has one line per request, and timestamps show ≥3 s between requests.
- `uv run python -m arengov diff <id> <id>` reports 0 new / 0 changed / 0 removed.

## Out of scope

HTML cleaning and text extraction belong to phase 02; this phase stores raw bytes only. The crawl runs once; if a category has fewer than 30 pages, record that in HANDOFF (D8 says `moving-to-the-uae` is the backup, and adding it is the owner's call).

## What you should understand after this phase

- **BFS crawling with a frontier, a visited set and a depth limit.** Why scope prefixes and caps keep a crawl bounded.
- **Politeness:** rate limiting, an honest User-Agent, robots.txt, backing off on 429/5xx. A crawler is a guest on someone else's server.
- **Snapshots:** why raw bytes + a manifest with `sha256` and `fetched_at` make the data reproducible and make "info may be outdated" concrete; how `diff` uses hashes.
- **Pairing by URL convention:** `page_id` links both language versions of a page, the foundation for cross-lingual evaluation later.
- **Testing I/O code** with a mock transport instead of the real network.

## Handoff checklist

- [ ] Acceptance criteria pass.
- [ ] HANDOFF: snapshot id, the summary table (pages per category/lang, missing AR mirrors), crawl duration, any odd pages.
- [ ] Committed on `phase-01-crawl`, pushed, PR open.
- [ ] Told the owner: merge when green, `/clear`, next is phase 02.
