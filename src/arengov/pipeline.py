from arengov import config
from arengov.index import load_index
from arengov.text_ar import tokenize


def retrieve(query, *, lang_filter=None, mode="bm25", use_rerank=True, use_norm=True):
    if mode != "bm25":
        raise ValueError(f"mode {mode!r} not available until phase 08")
    index = load_index()
    mask = index.langs == lang_filter if lang_filter else None
    bm25 = index.bm25 if use_norm else index.bm25_nonorm
    hits = bm25.search(tokenize(query, normalize=use_norm), config.BM25_TOP_N, mask)
    return {
        "candidates": hits[:20],
        "ranked": hits,
        "final": hits[: config.TOP_K_CONTEXT],
        "top_score": None,
        "stages": {"bm25": hits},
    }
