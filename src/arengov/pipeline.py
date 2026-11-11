import time

from arengov import config
from arengov.generate import generate, refusal_message
from arengov.index import load_index
from arengov.text_ar import detect_lang, tokenize


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


def answer(messages, answer_lang="auto"):
    t0 = time.perf_counter()
    question = next(m["content"] for m in reversed(messages) if m["role"] == "user")
    lang = detect_lang(question) if answer_lang == "auto" else answer_lang
    r = retrieve(question)
    index_chunks = load_index().chunks
    chunks = [index_chunks[i] for i, _ in r["final"]]
    g = generate(question, chunks, lang)
    if g["no_answer"]:
        seen, picked = set(), []
        for c in chunks:
            if c["page_id"] not in seen:
                seen.add(c["page_id"])
                picked.append(c)
        citations = [_citation(n, c) for n, c in enumerate(picked[:3], 1)]
        text, refused, reason = refusal_message(lang), True, "no_answer"
    else:
        citations = [_citation(n, chunks[n - 1]) for n in g["cited"]]
        text, refused, reason = g["answer"], False, None
    llm = g["llm"]
    return {
        "answer": text,
        "citations": citations,
        "refused": refused,
        "refusal_reason": reason,
        "lang": lang,
        "rewritten_query": question,
        "final_chunk_ids": [c["chunk_id"] for c in chunks],
        "usage": {
            "input_tokens": llm.input_tokens,
            "output_tokens": llm.output_tokens,
            "cost_usd": llm.cost_usd,
        },
        "latency_ms": (time.perf_counter() - t0) * 1000,
        "snapshot_id": chunks[0]["snapshot_id"] if chunks else None,
        "span_id": None,
        "_chunks": chunks,
    }
