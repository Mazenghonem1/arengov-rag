# Phase 16: Live demo on Hugging Face Spaces with hosted Phoenix

**Size:** ~4 h · **Depends on:** phase 15 merged; [YOU] accounts (task 0)

## Goal

A public URL serves the app on a free HF Space, sending traces to a second Space running Phoenix backed by a free Neon Postgres. All demo beats work live, the rerank latency rule is applied with real numbers, and an ops report comes from the live Phoenix.

## Decisions that apply

- Hosting (D44, D39):
  - **App Space** `arengov-rag`: Docker SDK, free CPU basic, the Dockerfile from phase 14, port 7860. Index downloaded at startup from the private dataset with a read `HF_TOKEN` (phase 15 `load_index`).
  - **Phoenix Space** `arengov-phoenix`: Docker SDK, `FROM arizephoenix/phoenix:<same pinned tag as compose>`, `PHOENIX_SQL_DATABASE_URL` = the Neon Postgres URL (persistent; Space disks are ephemeral), auth enabled, 30-day retention.
- Space secrets (D48): App gets `OPENAI_API_KEY`, `HF_TOKEN` (read), `PHOENIX_COLLECTOR_ENDPOINT`, `PHOENIX_API_KEY`. Phoenix gets `PHOENIX_SQL_DATABASE_URL`, `PHOENIX_SECRET`, plus the auth settings for the pinned version.
- **Rerank fallback (D25):** measure the p95 of the `rerank` span on the live Space over ≥ 20 requests. If it's > 3 s, set `RERANK_TOP_N = 10`, re-run `eval-retrieval --split test --label rerank10 --record`, ratchet nothing (thresholds must still pass), and redeploy.
- Beat 4 of the demo is shown in the GIF. A read-only Phoenix login goes in the README **only if** the pinned Phoenix version supports a viewer role; otherwise GIF only (D39).
- The README notes cold starts: free Spaces sleep after idle, and the first request can take ~1–2 min.
- The live demo stays up only while TDRA hasn't objected (D7).

## Tasks

0. **[YOU]**
   - Create a free Neon project (region close to HF's US/EU infrastructure) and copy its Postgres connection string.
   - Generate a random 32+ character `PHOENIX_SECRET`.
   - Put both in `.env` as `NEON_DATABASE_URL` and `PHOENIX_SECRET`.
   - Check the OpenAI project budget is still $15.
   - Values stay in `.env`; Claude reads them only inside scripts and never prints them.
1. **`deploy/phoenix/`:**
   - `Dockerfile` (`FROM arizephoenix/phoenix:<tag>`, plus `ENV` for port/host so it listens on `0.0.0.0:6006`);
   - `README.md` with HF Space front-matter (`title`, `sdk: docker`, `app_port: 6006`, `pinned: false`).
   Look up the auth and retention env vars in the docs for the pinned version and set the non-secret ones in the Dockerfile.
2. **`deploy/space/README.md`:** front-matter for the app Space (`sdk: docker`, `app_port: 7860`, a short description linking to the GitHub repo and the disclaimer).
3. **`scripts/deploy_spaces.py`** (argparse: `--phoenix`, `--app`, `--secrets`):
   - Uses `HfApi`: `create_repo(…, repo_type="space", space_sdk="docker", exist_ok=True)`.
   - Phoenix: `upload_folder(deploy/phoenix)`.
   - App: `upload_folder` of the repo root with `allow_patterns` = `Dockerfile, .dockerignore, pyproject.toml, uv.lock, .python-version, src/**, ui/**, eval/index_version.txt`, then `upload_file(deploy/space/README.md → README.md)`.
   - `--secrets` sets Space secrets from `.env` via `add_space_secret` and never prints values.
   - The app's `PHOENIX_COLLECTOR_ENDPOINT` = `https://<hf-user>-arengov-phoenix.hf.space`.
4. **Deploy Phoenix first.** Open its URL, log in as the admin, change the default admin password (owner), and create a **system API key** → put it in `.env` as `PHOENIX_API_KEY`. Set 30-day retention if it isn't set by env. Check whether a viewer role exists; if yes, create user `demo-viewer` with that role and give the owner the credentials.
5. **Deploy the app** (`--app --secrets`). Watch the build logs (model download ~5 GB, several minutes). Then `GET /api/health` and confirm the `index_version` matches.
6. **Live smoke test.** Click all 4 examples and type one EN and one AR question. Thumbs-down one answer → the annotation appears in the hosted Phoenix. Confirm traces are tagged with `arengov.git_sha` (set the `GIT_SHA` Space variable to the deployed commit in `deploy_spaces.py`).
7. **Latency:** make 20 requests in a loop (a 10-line inline Python using `httpx` with the example questions; keep it out of the repo). Then `uv run python scripts/ops_report.py --days 1` against the hosted Phoenix → p95 total latency and p95 of the `rerank` span (add rerank-span p95 to `compute_metrics` if it's missing, with a test). Apply the D25 rule.
8. Run `scripts/ops_report.py --days 1` against the hosted Phoenix and commit `docs/ops-report.md`.
9. Update `README.md`: the live demo link, the cold-start note, and the Phoenix viewer login or "see the GIF".

## Files

Create: `deploy/phoenix/Dockerfile`, `deploy/phoenix/README.md`, `deploy/space/README.md`, `scripts/deploy_spaces.py`. Change: `scripts/ops_report.py` (rerank p95, if needed) + its test, `config.py` (only if the D25 fallback triggers), `README.md`, `docs/ops-report.md`, `docs/results.md` (if `rerank10`), `docs/HANDOFF.md`.

## Acceptance criteria

- The live URL works from a logged-out browser: all 4 examples behave as designed, and the disclaimer is visible.
- Traces and the feedback annotation are visible in the hosted Phoenix and survive a Phoenix Space restart (restart it once to prove Neon persistence).
- The D25 rule was applied with measured numbers (recorded in HANDOFF).
- `uv run pytest -m "not slow"` passes; CI is green on the PR.

## Out of scope

Paid hardware, custom domains, autoscaling. If the free Space can't fit the models in memory, stop and report to the owner with the numbers; the fallback is D22's `multilingual-e5-small`, which requires an index rebuild and is the owner's call.

## What you should understand after this phase

- **Containers as the unit of deployment:** the same image ran locally in Compose and now on HF.
- **Stateless app + external state:** the app Space holds nothing; traces live in Postgres via Phoenix. That's why restarts lose nothing.
- **Cold starts** on free tiers, and why baked-in models matter.
- **Measuring before tuning:** the rerank fallback was decided in advance and applied from p95 data, not a hunch.
- **Operational security:** secrets in Space settings, a least-privilege token, the default admin password changed, an API key for trace ingestion.

## Handoff checklist

- [ ] Acceptance criteria pass.
- [ ] HANDOFF: both Space URLs, the Phoenix image tag, live p50/p95 latency and rerank p95, whether the D25 fallback triggered, the viewer-role result, the cold-start time observed.
- [ ] Committed on `phase-16-deploy`, pushed, PR open.
- [ ] Told the owner: merge when green, `/clear`, next is phase 17 (needs ~1 h of your time for the GIF).
