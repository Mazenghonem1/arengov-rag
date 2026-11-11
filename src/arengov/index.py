import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from arengov import config
from arengov.chunk import chunk_page, count_tokens
from arengov.clean import clean_html


@dataclass
class Index:
    chunks: list[dict]
    langs: np.ndarray


def build_index(snapshot_id: str, index_version: str) -> Path:
    out = config.INDEX_ROOT / index_version
    if out.exists():
        raise FileExistsError(f"{out} exists; pick a new version")
    snap = config.SNAPSHOT_ROOT / snapshot_id
    pages = [json.loads(line) for line in (snap / "manifest.jsonl").read_text("utf-8").splitlines()]
    chunks: list[dict] = []
    kept, skipped = Counter(), Counter()
    for r in pages:
        if r["http_status"] != 200:
            continue
        title, md = clean_html((snap / r["raw_path"]).read_text("utf-8"))
        if len(md) < config.MIN_PAGE_CHARS:
            skipped[r["lang"]] += 1
            print(f"skip {r['url']} ({len(md)} chars)")
            continue
        kept[r["lang"]] += 1
        meta = {**{k: r[k] for k in ("page_id", "url", "lang", "pair_url", "category")}}
        chunks += chunk_page(title, md, {**meta, "snapshot_id": snapshot_id})

    sizes = [count_tokens(c["text"]) for c in chunks]
    assert max(sizes) <= config.CHUNK_MAX_TOKENS, f"chunk over limit: {max(sizes)} tokens"

    out.mkdir(parents=True)
    with (out / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        sha = "unknown"
    meta_out = {
        "index_version": index_version,
        "snapshot_id": snapshot_id,
        "embed_model": None,
        "n_chunks": len(chunks),
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_sha": sha,
    }
    (out / "meta.json").write_text(json.dumps(meta_out, indent=2), "utf-8")

    print(f"pages kept {dict(kept)}, skipped {dict(skipped)}")
    print(f"chunks per lang {dict(Counter(c['lang'] for c in chunks))}")
    print(f"chunks per category {dict(Counter(c['category'] for c in chunks))}")
    print(f"tokens mean {sum(sizes) / len(sizes):.1f}, max {max(sizes)}")
    return out


def load_index(version: str | None = None) -> Index:
    version = version or config.INDEX_VERSION_FILE.read_text("utf-8").strip()
    path = config.INDEX_ROOT / version / "chunks.jsonl"
    chunks = [json.loads(line) for line in path.read_text("utf-8").splitlines()]
    return Index(chunks=chunks, langs=np.array([c["lang"] for c in chunks]))
