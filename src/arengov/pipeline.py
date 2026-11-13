import time

from arengov import config
from arengov.generate import generate, refusal_message
from arengov.index import load_index
from arengov.retrieve import collapse_pairs, dense_search, rrf
from arengov.rewrite import rewrite
from arengov.text_ar import detect_lang, tokenize


def retrieve(query, *, lang_filter=None, mode="hybrid", use_rerank=True, use_norm=True):
    if mode not in ("bm25", "dense", "hybrid"):
        raise ValueError(f"unknown mode {mode!r}")
    index = load_index()
    mask = index.langs == lang_filter if lang_filter else None
    bm25, dense = [], []
    if mode in ("bm25", "hybrid"):
        bm25_index = index.bm25 if use_norm else index.bm25_nonorm
        bm25 = bm25_index.search(tokenize(query, normalize=use_norm), config.BM25_TOP_N, mask)
    if mode in ("dense", "hybrid"):
        if index.embeddings is None:
            raise RuntimeError("index has no embeddings; rebuild with --embed")
        from arengov.embed import embed_query  # lazy: importing torch is slow

        dense = dense_search(embed_query(query), index.embeddings, config.DENSE_TOP_N, mask)
    if mode == "bm25":
        cands = bm25[: config.FUSED_TOP_N]
    elif mode == "dense":
        cands = dense[: config.FUSED_TOP_N]
    else:
        cands = rrf([[i for i, _ in bm25], [i for i, _ in dense]])[: config.FUSED_TOP_N]
    if use_rerank and cands:
        from arengov.rerank import rerank  # lazy: importing torch is slow

        reranked = rerank(query, index.chunks, [i for i, _ in cands[: config.RERANK_TOP_N]])
        top_score = reranked[0][1]
    else:
        reranked, top_score = cands, None
    ranked = collapse_pairs(reranked, index.chunks)
    return {
        "candidates": cands,
        "ranked": ranked,
        "final": ranked[: config.TOP_K_CONTEXT],
        "top_score": top_score,
        "stages": {"bm25": bm25, "dense": dense, "reranked": reranked},
    }


def _snippet(text):
    # drop the heading line the chunk starts with
    body = (text.split("\n", 1)[1] if "\n" in text else text).strip()
    limit = config.SNIPPET_MAX_CHARS
    if len(body) <= limit:
        return body
    return body[:limit].rsplit(" ", 1)[0] + "…"


def _citation(n, c):
    return {
        "n": n,
        "url": c["url"],
        "title": c["title"],
        "lang": c["lang"],
        "snippet": _snippet(c["text"]),
        "pair_url": c["pair_url"],
    }


def _refusal(chunks):
    # up to 3 closest distinct pages, numbered 1-3
    seen, picked = set(), []
    for c in chunks:
        if c["page_id"] not in seen:
            seen.add(c["page_id"])
            picked.append(c)
    return [_citation(n, c) for n, c in enumerate(picked[:3], 1)]


def answer(messages, answer_lang="auto"):
    t0 = time.perf_counter()
    user_msgs = [m["content"] for m in messages if m["role"] == "user"]
    question = user_msgs[-1]
    prev = user_msgs[:-1][-config.HISTORY_MAX_TURNS :]
    lang = (
        detect_lang(question) if answer_lang == "auto" else answer_lang
    )  # original, not rewritten
    rewritten, rw = rewrite(prev, question, lang) if prev else (question, None)
    r = retrieve(rewritten)
    index_chunks = load_index().chunks
    chunks = [index_chunks[i] for i, _ in r["final"]]
    tau, top = config.GATE_TAU, r.get("top_score")
    if tau is not None and top is not None and top < tau:
        g = None  # gate: no LLM call
        citations, text, reason = _refusal(chunks), refusal_message(lang), "gate"
        refused, invalid = True, []
    else:
        g = generate(rewritten, chunks, lang)
        invalid = g["invalid_citations"]
        if g["no_answer"]:
            citations, text, reason = _refusal(chunks), refusal_message(lang), "no_answer"
            refused = True
        else:
            citations = [_citation(n, chunks[n - 1]) for n in g["cited"]]
            text, refused, reason = g["answer"], False, None
    llm = g["llm"] if g else None
    parts = [x for x in (rw, llm) if x]
    return {
        "answer": text,
        "citations": citations,
        "refused": refused,
        "refusal_reason": reason,
        "invalid_citations": invalid,  # needed by the citation_valid eval check
        "lang": lang,
        "rewritten_query": rewritten,
        "final_chunk_ids": [c["chunk_id"] for c in chunks],
        "usage": {
            "input_tokens": sum(x.input_tokens for x in parts),
            "output_tokens": sum(x.output_tokens for x in parts),
            "cost_usd": sum(x.cost_usd for x in parts),
        },
        "latency_ms": (time.perf_counter() - t0) * 1000,
        "snapshot_id": chunks[0]["snapshot_id"] if chunks else None,
        "span_id": None,
        "_chunks": chunks,
    }
