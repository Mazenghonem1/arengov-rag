# Phase 02: Clean HTML and chunk into an index

**Size:** ~3 h · **Depends on:** phase 01 merged; a snapshot exists in `data/snapshots/`

## Goal

`uv run python -m arengov build-index --snapshot <id> --version <id>-v1` turns raw pages into clean Markdown-like text and heading-aware chunks of ≤400 tokens, written to `data/index/<id>-v1/chunks.jsonl`, and records the version in `eval/index_version.txt`.

## Prerequisites

- Snapshot from phase 01 (the id is in HANDOFF).

## Decisions that apply

- Cleaning (D20): BeautifulSoup + lxml with a **u.ae-specific main-content selector** found by inspecting real pages. Drop nav, footer, breadcrumbs, feedback widgets ("was this page helpful"), share bars, scripts. Output keeps H1–H4 as `#` headings, paragraphs, list items as `- `, and tables as rows `Header: value; Header: value`. **Link text kept, href dropped** (D60b). Pages with <200 characters after cleaning are skipped and logged.
- Chunking (D21): split on H2/H3; pack paragraphs up to `CHUNK_MAX_TOKENS = 400` counted with the **bge-m3 tokenizer**; only over-long sections split, with one paragraph of overlap. Each chunk's `text` starts with the `heading_path` line. Record fields and `chunk_id` format: PLAN.md § Records.
- Test fixtures are **synthetic HTML** copying u.ae's DOM structure with invented text, never real page content (D59).
- Index layout and versioning: PLAN.md § Paths. The first version is `<snapshot_id>-v1`.

## Tasks

1. `uv add tokenizers`. If `Tokenizer.from_pretrained` needs it, also `uv add huggingface_hub`.
2. Add the `[02]` constants to `config.py`.
3. **Inspect real pages.** Pick 5 raw files from the manifest: 2 EN content pages, 2 AR content pages, 1 category landing page. For each, find:
   - the element that holds the main content (`CONTENT_SELECTOR`);
   - the noise elements inside it (`DROP_SELECTORS`);
   - which tags hold the visible text.
   Print visible text (container `get_text`) next to what your tag walk captures. If more than 10% of the container's visible text sits in tags outside `h1–h4, p, li, table`, add those tags to the walk and note it in HANDOFF. Show the owner one cleaned page in each language before continuing.
4. **`src/arengov/clean.py`:** module constants `CONTENT_SELECTOR`, `DROP_SELECTORS` from task 3. `clean_html(html) -> (title, markdown)`:
   - Parse with lxml. Remove `script, style, noscript` and `DROP_SELECTORS`. Select the content container; if it's missing, return `("", "")`.
   - Title = text of the first `h1` in the container, else `<title>` with any site suffix removed.
   - Walk `container.find_all(["h1","h2","h3","h4","p","li","table"])` in document order. Skip an element when one of its ancestors (below the container) is a `p`, `li` or `table`. Emit:
     - `h1–h4` → `"#"*level + " " + text`
     - `p` → text
     - `li` → `"- " + text`
     - `table` → if the first row has `th` cells, each later row becomes `"H1: v1; H2: v2"`; otherwise cells are joined with `" | "`.
   - Text = `get_text(" ", strip=True)` with whitespace collapsed. Drop empty blocks and exact consecutive duplicates. Join blocks with `"\n\n"`.
5. **`src/arengov/chunk.py`:**
   - `count_tokens(text)`: a cached `tokenizers.Tokenizer.from_pretrained(TOKENIZER_MODEL)`; `len(tok.encode(text, add_special_tokens=False).ids)`.
   - `chunk_page(title, markdown, meta)`:
     - Split blocks on `"\n\n"` and walk them, tracking current H2 and H3. An H2 block resets H3. H1 blocks are ignored (the title covers them). H4 blocks stay as paragraph text.
     - A section = consecutive non-heading blocks under the same (H2, H3). Content before the first H2 is a section with `heading_path` = title only.
     - `heading_path` = `" > ".join` of the non-empty parts of `[title, h2, h3]`.
     - Packing: add paragraphs greedily while `count_tokens(heading_path + "\n" + body) <= CHUNK_MAX_TOKENS`. When the next paragraph doesn't fit, close the chunk and start the next one with the **last paragraph of the closed chunk** (overlap), unless that paragraph + the new one together exceed the limit; then start without overlap.
     - A single paragraph over the limit: split into sentences (regex `(?<=[.!?؟])\s+`) and pack those. A single sentence over the limit: split on whitespace into word groups that fit.
     - Sections with an empty body produce no chunk.
     - Return records with all fields from PLAN.md § Records. `meta` supplies `page_id, url, lang, pair_url, snapshot_id, category`, and `chunk_id = f"{lang}:{page_id}:{i}"`.
6. **`src/arengov/index.py`:**
   - `build_index(snapshot_id, index_version)`: read the manifest (status 200 only); for each page `clean_html` its raw file; skip pages with `len(markdown) < MIN_PAGE_CHARS` (log url + length); `chunk_page`; write `INDEX_ROOT/<version>/chunks.jsonl` and `meta.json` (`embed_model: null` for now; `git_sha` from `git rev-parse --short HEAD` or `"unknown"`). Refuse to overwrite an existing version folder. Assert every chunk has `count_tokens(text) <= CHUNK_MAX_TOKENS`. Print stats: pages kept/skipped per lang, chunks per lang and per category, token mean/max.
   - `Index` dataclass with `chunks: list[dict]` and `langs: np.ndarray` (`uv add numpy`). `load_index(version=None)`: version defaults to the text of `INDEX_VERSION_FILE`, stripped.
7. **CLI:** `build-index --snapshot ID --version VERSION` runs `build_index`, then writes `VERSION` into `eval/index_version.txt`.
8. **Tests** (`tests/test_clean.py`, `tests/test_chunk.py`, fixtures in `tests/fixtures/`):
   - Two synthetic fixtures, `uae_en.html` and `uae_ar.html`, that mimic the real DOM: header/nav, breadcrumbs, the content container with h1/h2/h3/p/ul/table and a link, a feedback widget inside the container, a footer. All text invented. The Arabic one uses Arabic text with diacritics and Arabic-Indic digits.
   - `clean_html` keeps headings, list items and table rows as specified; noise, nav and footer text are absent; no `http` from hrefs appears; the title is correct.
   - `chunk_page` with `chunk.count_tokens` monkeypatched to word count and a small limit (e.g. 20): heading_path correct; the limit holds; overlap paragraph present; the over-long sentence is split; empty sections are skipped; `chunk_id`s are sequential.
   - One `@pytest.mark.slow` test calls the real `count_tokens` on an Arabic sentence and checks it returns a positive int.
9. **Build the real index:** `build-index --snapshot <id> --version <id>-v1`. Print 3 random chunks per language for the owner to eyeball.

## Files

Create: `src/arengov/clean.py`, `src/arengov/chunk.py`, `src/arengov/index.py`, `tests/test_clean.py`, `tests/test_chunk.py`, `tests/fixtures/uae_en.html`, `tests/fixtures/uae_ar.html`, `eval/index_version.txt`. Change: `config.py`, `__main__.py`, `pyproject.toml`, `uv.lock`, `docs/HANDOFF.md`.

## Acceptance criteria

- `uv run pytest` (including slow) passes; ruff clean.
- `data/index/<id>-v1/chunks.jsonl` exists; the in-build assert passed (all chunks ≤400 tokens); there are chunks in both languages and all 3 categories.
- `eval/index_version.txt` contains `<id>-v1` and is committed.
- The owner has looked at one cleaned page per language and at 6 random chunks and agrees they're clean (record that in HANDOFF).

## Out of scope

The index holds chunks only; embeddings arrive in phase 08 and BM25 in phase 03. Tokenization for search (normalization, stemming) is phase 03's `text_ar.py`. This phase only counts tokens for chunk size.

## What you should understand after this phase

- **Boilerplate removal:** why a site-specific selector beats generic extraction here, and how you verified it (captured vs visible text).
- **Chunking trade-offs:** small chunks are precise but lose context, big chunks dilute embeddings. Splitting on headings uses the author's own structure. The `heading_path` prefix gives every chunk its context ("fee" for *which* visa).
- **Tokens ≠ words ≠ characters,** especially for Arabic. Why we count with the embedding model's own tokenizer.
- **Index versioning:** an index is a build artifact identified by `<snapshot>-vN`, and every eval number later is tied to one version.

## Handoff checklist

- [ ] Acceptance criteria pass.
- [ ] HANDOFF: selectors chosen, index version, stats (pages kept/skipped, chunks per lang/category, token mean/max), owner's eyeball verdict.
- [ ] Committed on `phase-02-clean-chunk`, pushed, PR open.
- [ ] Told the owner: merge when green, `/clear`, next is phase 03.
