import functools
import json
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from arengov import config
from arengov.bm25 import BM25
from arengov.chunk import chunk_page, count_tokens
from arengov.clean import clean_html
from arengov.text_ar import tokenize


@dataclass
class Index:
    chunks: list[dict]
    langs: np.ndarray
    embeddings: np.ndarray | None = None

    @functools.cached_property
    def bm25(self) -> BM25:
        return BM25([tokenize(c["text"]) for c in self.chunks])

    @functools.cached_property
    def bm25_nonorm(self) -> BM25:  # ablation index, built only when asked for
        return BM25([tokenize(c["text"], normalize=False) for c in self.chunks])


def build_index(snapshot_id: str, index_version: str, embed: bool = False) -> Path:
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
    if embed:
        from arengov.embed import device, embed_texts

        t0 = time.perf_counter()
        emb = embed_texts([c["text"] for c in chunks])  # raw text, never normalized (D16)
        assert emb.shape == (len(chunks), 1024), emb.shape
        np.save(out / "embeddings.npy", emb)
        print(f"embedded {len(chunks)} chunks on {device()} in {time.perf_counter() - t0:.0f}s")
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        sha = "unknown"
    meta_out = {
        "index_version": index_version,
        "snapshot_id": snapshot_id,
        "embed_model": config.EMBED_MODEL if embed else None,
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


@functools.cache
def load_index(version: str | None = None) -> Index:
    version = version or config.INDEX_VERSION_FILE.read_text("utf-8").strip()
    path = config.INDEX_ROOT / version / "chunks.jsonl"
    chunks = [json.loads(line) for line in path.read_text("utf-8").splitlines()]
    emb_path = path.with_name("embeddings.npy")
    emb = np.load(emb_path) if emb_path.exists() else None
    if emb is not None:
        assert emb.shape == (len(chunks), 1024), emb.shape
    return Index(chunks=chunks, langs=np.array([c["lang"] for c in chunks]), embeddings=emb)
