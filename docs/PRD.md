# PRD: arengov-rag

Bilingual Arabic–English assistant for UAE government services, built as a portfolio project.
Owner: Mazen Ghonem. Date: 2026-11-09. Decisions referenced as D-numbers live in `docs/DECISIONS.md`.

## Problem

People moving to or working in the UAE need answers about visas, Emirates ID, work permits and business licensing. The official portal u.ae has the information in Arabic and English, but it's spread over hundreds of pages. Keyword search fails when the user's wording or language differs from the page's.

## Goal

A chat assistant that answers questions about these topics **only from u.ae pages**:
- with numbered citations linking to the source page,
- in the language the user asked in (Arabic or English),
- even when the best source is in the other language,
- and that **refuses** when the pages don't contain the answer.

The portfolio goal matters as much as the product goal. The project demonstrates a measurable, monitored, deployed RAG system whose every component the owner can explain.

## Users

- **In-app persona (D1):** a new expat or resident handling visa, Emirates ID, work and business-setup tasks, who writes in Arabic or English.
- **Audience of the project:** recruiters and hiring engineers. A recruiter must understand the demo in **under 5 minutes**.

## The 5-minute demo (D2)

1. Click an English example → English answer with `[1][2]` citations to u.ae.
2. Click an Arabic example → Arabic answer citing an **English** page. Then click the Arabic follow-up ("وماذا عن تجديدها؟", "what about renewing it?") → answered via query rewriting.
3. Click the off-topic example → polite refusal in the same language, with links to related pages.
4. Thumbs-down → the trace in Phoenix: chunks, prompt, latency, cost (shown in the GIF).
5. The README results table and the green CI eval badge.

## Scope (must-have)

- **Data:** polite crawl of 3 u.ae categories (`visa-and-emirates-id`, `jobs`, `business`), ~200 EN pages + Arabic mirrors, dated snapshots with manifest, manual refresh + diff (D6–D12).
- **Pipeline (plain Python):** clean → heading-aware chunks → Arabic-aware BM25 + bge-m3 dense → RRF → bge-reranker → pair collapse → LLM answer with `[n]` citations → two-layer refusal (D15–D26, D31).
- **Multi-turn chat:** follow-ups via LLM query rewriting; history only in the browser; no login (D3, D58).
- **LLMs:** OpenAI `gpt-5.6-luna` (generation, rewriting), `gpt-5.6-terra` (judge), local `qwen3:8b` via Ollama as the free option (D27–D29).
- **Evaluation:** 60 hand-written questions (half AR, half EN; single-turn, multi-turn, unanswerable, mixed-script), dev/test split. Retrieval metrics, deterministic answer checks, LLM judge validated against the owner's blind grades (D32–D38).
- **CI:** tests + retrieval eval gate on every change, answer eval gate on prompt/generation changes (D47).
- **Monitoring:** self-hosted Phoenix, one trace per request, thumbs feedback as annotations, ops report (p95 latency, cost/query, no-answer rate, feedback rate), manual feedback→eval-case loop, PII scrubbing (D39–D43).
- **Deployment:** FastAPI + static UI, Docker Compose locally, free HF Spaces for the app and Phoenix, spend guardrails (D30, D44–D46).
- **Repo quality:** README with GIF, results table, Mermaid diagram, DECISIONS, MIT license (D49–D50).

## Stretch (only if must-haves finish on time, D4)

- Online judge on sampled production traces (weekly scheduled job).
- Automated feedback → eval-case export.
- Custom dashboard page.
- Bilingual query expansion for BM25 (D19).

## Non-goals

- Login, accounts, server-side chat history, cross-session memory (D3).
- Other portals (Hukoomi, ICP, GDRFA, emirate-level sites), other u.ae categories (D6, D8).
- Scheduled re-crawling (D12).
- Form filling, applications, or any action on the user's behalf.
- Streaming responses (D45).
- A vector database (D23).
- Official or legal advice of any kind.

## Constraints

- Public data only; polite crawling; crawled text never committed; snippets ≤300 chars + links in the UI; bilingual disclaimer; takedown contact; permission email to TDRA (D7, D55).
- No personal data: scrub before logging, no IPs, 30-day retention (D43).
- Nothing from the owner's employer.
- ~66 hours over ~7 weeks at 9–10 h/week (D14, D52).
- Spend: OpenAI project budget $15/month; demo rate limits (D30).

## Success metrics

The project is **done** (D5) when all of these hold:
1. A public GitHub repo with a green CI badge, where CI runs tests + retrieval eval gate + answer eval gate.
2. A live demo URL serving all 5 demo beats, plus a demo GIF in the README.
3. A README results table on the **test** split, reporting:
   - retrieval: recall@5, recall@20, MRR@10, by language and in cross-lingual mode, with ablations (BM25 / dense / hybrid / +rerank / normalization off);
   - answers: refusal correctness, language match, faithfulness, correctness, citation accuracy, p95 latency, cost/question, for both the OpenAI and the local Qwen backend;
   - judge validation: agreement % and Cohen's κ per criterion.
4. Every phase doc complete, `docs/HANDOFF.md` current, and an ops report generated from real traffic.

Quality targets are set from data, not guessed. The first baseline sets CI thresholds (baseline − 5 pts, D37), and each later phase must beat or match it. Judge targets: ≥85% agreement and κ ≥ 0.6 per criterion (D38).

## Risks

| Risk | Mitigation |
|---|---|
| TDRA objects to the use of content | Snippets + links only, nothing committed, takedown promise; the live demo comes down if asked (D7). |
| u.ae changes its HTML or starts blocking | Dated snapshots; site-specific selector covered by fixture tests; crawl stops on errors. |
| bge-m3 + reranker too slow on 2 free vCPUs | Measured fallback rule: rerank top-10 instead of top-20 (D25); e5-small as embedding fallback (D22). |
| Timeline overrun | Stretch list above; phases are ordered so a cut leaves a working, measured system. |
| Judge disagrees with the owner | Measured, revised once on dev, reported honestly (D38). |
