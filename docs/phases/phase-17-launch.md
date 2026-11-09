# Phase 17: Launch: comparison row, README, diagram, GIF

**Size:** ~4 h (3 h Claude, 1 h [YOU] GIF) · **Depends on:** phase 16 merged · **Cost:** ~$0.07–0.15 (judging the Qwen row, plus a luna re-run only if phase 16 changed the pipeline)

## Goal

The repo tells the whole story in under 5 minutes. A recruiter sees the GIF, the live link and the results table on the first screen, and an engineer finds the architecture, the design decisions and the honest limitations. The local-model comparison row is measured, and v1.0 is tagged.

## Decisions that apply

- README order (D49):
  1. pitch
  2. live demo link + GIF
  3. disclaimer
  4. results table
  5. Mermaid architecture diagram
  6. how it works, one paragraph per stage
  7. run locally
  8. design decisions (link to `docs/DECISIONS.md`)
  9. limitations
  10. legal / takedown
- Results table (D49): **test split**. Rows:
  - BM25, dense, hybrid, + rerank (the final pipeline);
  - cross-lingual recall@5 for BM25 / dense / hybrid+rerank;
  - normalization off;
  - answers for `gpt-6-luna` vs local `qwen3:8b`, both judged by `gpt-6.1-terra` with the **final** judge prompt from phase 11 (D68);
  - judge agreement + κ per criterion;
  - live ops numbers (p95 latency, cost/query) from `docs/ops-report.md`.
  State "n = 20 test questions; 1 question ≈ 5 points".
- GIF (D49): ScreenToGif, ≤ 10 MB, `docs/demo.gif`. Beats 1–4 from D2: EN question → AR question citing EN → AR follow-up → off-topic refusal → thumbs-down → the trace in Phoenix.
- MIT license; content belongs to TDRA, isn't included and isn't licensed (D50).

## Tasks

1. **Answer rows for the README** (the only OpenAI spend in this phase):
   - **Luna row:** use the latest test summary that matches the deployed pipeline and the final judge prompt. That's phase 10's `rewrite` test run, or its `-rejudge` version if phase 11 revised the judge prompt. Exception: if phase 16 changed the pipeline (e.g. the D25 rerank fallback), re-run `eval-answers --split test --label final --record` (~$0.08) and use that.
   - **Qwen row:** with Ollama running, `eval-answers --split test --backend ollama --label qwen3-8b --record` (generation is free; judging ~$0.07). Note latency differences honestly (local GPU vs API).
   - Confirm both summaries show `judge_model: gpt-6.1-terra` before copying numbers into the README.
2. **`README.md`**, full rewrite in the D49 order:
   - **Pitch** (2 sentences) + badges (CI, license) + **live demo link** + `![demo](docs/demo.gif)`.
   - **Disclaimer** EN + AR (text from `phase-00-setup.md`).
   - **Results:** one compact table of the rows above, built from `docs/results.md` (copy the numbers; link to the full log). One sentence each on what hybrid, the reranker and cross-lingual mode show. One line on judging: "Answer metrics judged by gpt-6.1-terra, validated against blind human grades (agreement X%, κ Y); the same judge gates CI." Link the gate-demo PR ("CI blocks regressions: example").
   - **Architecture:** a Mermaid `flowchart LR`: Crawler → Snapshot → Clean/Chunk → {BM25 index, bge-m3 embeddings} → Retrieval (BM25 + dense → RRF → reranker → pair collapse → gate) → LLM (gpt-6-luna / qwen3:8b) → Answer + citations → UI. Phoenix receives traces; feedback flows back into Phoenix and then the eval set; CI runs the eval against thresholds. Keep it ≤ 20 nodes.
   - **How it works:** one short paragraph per stage (crawl, clean+chunk, Arabic-aware BM25, dense, RRF, rerank+collapse, refusal gate, generation with citations, query rewriting, evaluation, judge validation, tracing+feedback, CI gates, deployment). Each paragraph names the file in `src/arengov/`.
   - **Why no vector DB:** 3 sentences (scale, exact search, when to switch).
   - **Run locally:** `uv sync`, `.env`, `crawl` → `build-index --embed` → `ask`; `docker compose up`; eval commands. Mention that the data is not included and you must crawl it yourself, politely.
   - **Design decisions:** a link to `docs/DECISIONS.md` and `docs/PLAN.md`.
   - **Limitations:** 3 categories only; one snapshot date; the live demo pauses when its small OpenAI credit runs out (the GIF shows it working); a 20-question test set (noisy); a single-annotator judge validation; free-tier cold starts; no official status; the detection heuristic for mixed-script language; translations may differ from the source page.
   - **Legal / takedown:** the content belongs to TDRA; not included; open an issue for removal; the TDRA email status.
3. **[YOU] Record the GIF** (~1 h with retakes) following the beat list, at a 1280×720 window, then crop and optimize in ScreenToGif to ≤ 10 MB. Save it as `docs/demo.gif`. Claude checks the size and that it renders in the README preview.
4. **Final ops report:** regenerate `docs/ops-report.md` from the hosted Phoenix (`--days 30`).
5. **Tick the PRD success metrics:** add a "Status" line under each success metric in `docs/PRD.md` (✅ / ❌ with a link).
6. **Update `docs/PLAN.md`:** mark every phase done and list what's left in the stretch backlog.
7. Commit, push, PR. After the owner merges: `git tag v1.0 && git push origin v1.0` and `gh release create v1.0 --title "v1.0" --notes "<3-line summary + results table link>"`.

## Files

Create: `docs/demo.gif` ([YOU]). Change: `README.md`, `docs/results.md`, `docs/ops-report.md`, `docs/PRD.md`, `docs/PLAN.md`, `docs/HANDOFF.md`.

## Acceptance criteria

- The README renders on GitHub with the GIF, the Mermaid diagram and the results table; every number in it matches `docs/results.md`.
- A test reader (the owner, with a timer) gets the story from the README + live demo in < 5 minutes.
- The luna and `qwen3-8b` answer rows have `judge_model = gpt-6.1-terra` and the final judge prompt, and every answer number in the README comes from them; `docs/demo.gif` is ≤ 10 MB.
- CI is green; the `v1.0` tag and release exist after the merge.

## Out of scope

Stretch items (online judge, automated feedback export, dashboard page, bilingual query expansion) start only after v1.0, each as its own phase planned with the owner.

## What you should understand after this phase

- **Communicating ML work:** lead with a demo and numbers, then explain mechanisms, then admit limits.
- **Honest reporting:** sample size, held-out test split, judge validation, a local model that's slower or worse are all strengths in an interview, not weaknesses.
- **The whole loop you built:** data → pipeline → offline eval → CI gate → deployment → tracing → feedback → new eval cases. Be ready to walk through it on a whiteboard in 5 minutes.

## Handoff checklist

- [ ] Acceptance criteria pass.
- [ ] HANDOFF: final status, links (repo, live demo, Phoenix, release), the stretch backlog.
- [ ] Committed on `phase-17-launch`, pushed, PR open; tag + release after the merge.
- [ ] Told the owner: the project is at v1.0. 🎉
