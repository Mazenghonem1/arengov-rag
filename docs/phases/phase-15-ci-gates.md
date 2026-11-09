# Phase 15: Index hosting and eval gates in CI

**Size:** ~3 h · **Depends on:** phase 14 merged; [YOU] a Hugging Face account and tokens (task 0)

## Goal

The built index lives in a private Hugging Face dataset repo, versioned. GitHub Actions downloads the pinned version and **fails a PR when retrieval or answer quality drops below `eval/thresholds.json`**, and a deliberate regression proves it.

## Decisions that apply

- Index artifacts (`chunks.jsonl`, `embeddings.npy`, `meta.json`) go to the **private** dataset repo `<hf-user>/arengov-index`, one folder per `index_version` (D44). Private storage isn't redistribution (D7).
- CI jobs (D47):
  - `test` (exists): every push/PR.
  - `eval-retrieval`: on push to main and every PR. It downloads the pinned index (`eval/index_version.txt`), caches HF models with `actions/cache`, runs retrieval eval on **test**, then `check-thresholds`. It needs `OPENAI_API_KEY` for the multi-turn rewrites (~$0.002, D58) and `HF_TOKEN`.
  - `eval-answers`: on PRs that touch generation-related files, plus `workflow_dispatch`. Full answer eval on **test** (~$0.25), then `check-thresholds`.
- CI never crawls and never rebuilds the index. Changing cleaning/chunking/embedding means rebuilding locally, `upload-index`, and bumping `eval/index_version.txt` in the same PR (D47, CLAUDE.md hard rules).
- Secrets: `OPENAI_API_KEY`, `HF_TOKEN` as GitHub Actions secrets (D48).

## Tasks

0. **[YOU]** On huggingface.co: create (1) a **write** token for uploads (store it locally as `HF_TOKEN` in `.env`) and (2) a fine-grained **read** token limited to the `arengov-index` repo for CI and the Space. Add the GitHub secrets yourself, because values must not pass through the chat: `gh secret set HF_TOKEN` (paste the read token) and `gh secret set OPENAI_API_KEY`. Tell Claude your HF username if it isn't `Mazenghonem1`.
1. `uv add huggingface_hub` (if not already present). Add `HF_INDEX_REPO = f"{os.environ.get('HF_USER', 'Mazenghonem1')}/arengov-index"` to `config.py`.
2. **`index.py`:**
   - `upload_index(version)`: `HfApi().create_repo(HF_INDEX_REPO, repo_type="dataset", private=True, exist_ok=True)`, then `upload_folder(folder_path=INDEX_ROOT/version, path_in_repo=version, repo_id=…, repo_type="dataset", commit_message=f"index {version}")`.
   - `download_index(version)`: `snapshot_download(repo_id=…, repo_type="dataset", allow_patterns=[f"{version}/*"], local_dir=INDEX_ROOT)`.
   - `load_index`: when the version folder is missing and `HF_TOKEN` is set, call `download_index` first (used by CI and by the Space at startup).
3. **CLI:** `upload-index [--version V]` and `download-index [--version V]` (default: `eval/index_version.txt`).
4. Upload the current index version and verify: delete a local copy in a temp location, download it, and compare the sha256 of all 3 files.
5. **`.github/workflows/ci.yml`:** add job `eval-retrieval` (`needs: test`; triggers as above):
   - checkout, setup-uv, `uv sync --locked`;
   - `actions/cache` for `~/.cache/huggingface`, keyed on `hf-${{ hashFiles('src/arengov/config.py') }}`;
   - env `HF_TOKEN`, `OPENAI_API_KEY` from secrets;
   - `uv run python -m arengov download-index`;
   - `uv run python -m arengov eval-retrieval --split test --label ci --out ci-retrieval.json`;
   - `uv run python -m arengov check-thresholds ci-retrieval.json`;
   - upload `ci-retrieval.json` as an artifact.
6. **`.github/workflows/eval-answers.yml`:** `on: pull_request` with `paths`: `src/arengov/generate.py`, `llm.py`, `rewrite.py`, `pipeline.py`, `retrieve.py`, `rerank.py`, `judge.py`, `eval_answers.py`, `config.py`, `eval/questions.jsonl`, `eval/thresholds.json`, `eval/index_version.txt`; plus `workflow_dispatch`. One job with the same setup, then `eval-answers --split test --label ci --out ci-answers.json`, `check-thresholds ci-answers.json`, and the artifact upload.
7. **README:** add the CI badge for `ci.yml` at the top.
8. **Prove the gate** on a throwaway branch `gate-demo` from this phase's branch: set `TOP_K_CONTEXT = 1` in `config.py`, push, and open a draft PR titled "Demo: eval gate catches a regression (do not merge)". Both eval jobs should go red on `recall@5` (and answer metrics). Save the PR link for the README, then close the PR without merging and delete the branch.
9. Commit, push this phase's branch, and open the PR. All checks should be green, and `eval-answers` runs because this PR touches `config.py`.

## Files

Create: `.github/workflows/eval-answers.yml`. Change: `.github/workflows/ci.yml`, `src/arengov/index.py`, `src/arengov/config.py`, `src/arengov/__main__.py`, `README.md`, `pyproject.toml`, `uv.lock`, `docs/HANDOFF.md`. Tests: add `tests/test_index_download.py` (monkeypatch `snapshot_download`: `load_index` triggers a download only when the folder is missing and `HF_TOKEN` is set).

## Acceptance criteria

- `uv run pytest -m "not slow"` passes; ruff clean.
- The phase PR shows `test`, `eval-retrieval` and `eval-answers` all green, with CI metrics matching the latest local test rows (identical, or within one question).
- The `gate-demo` PR showed red eval checks, and its link is saved in HANDOFF.
- The HF dataset repo is **private** (check it in the browser while logged out, or via `HfApi().repo_info(...).private`).

## Out of scope

CI uses the pinned index and only evaluates; deployment is phase 16. The scheduled online-judge workflow is stretch (D42).

## What you should understand after this phase

- **Eval as a CI gate:** the same idea as unit tests, applied to model quality. A PR that silently makes answers worse can't merge.
- **Why retrieval runs on every PR and answers only on some:** cost and time vs risk.
- **Pinned artifacts:** CI evaluates a fixed index version, so a metric change can come only from the code in the PR.
- **Secrets hygiene:** least-privilege read token for CI, write token only on your machine, secrets entered by you instead of passing through chat.
- **Proving a safety mechanism works** by breaking things on purpose.

## Handoff checklist

- [ ] Acceptance criteria pass.
- [ ] HANDOFF: the HF repo id, the uploaded version, CI run times per job, the gate-demo PR link.
- [ ] Committed on `phase-15-ci-gates`, pushed, PR open.
- [ ] Told the owner: merge when green, `/clear`, next is phase 16 (needs a Neon account).
