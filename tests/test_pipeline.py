from types import SimpleNamespace

from arengov import pipeline
from arengov.llm import LLMResult


def _chunk(i, page, lang="en"):
    return {
        "chunk_id": f"{lang}:{page}:{i}",
        "page_id": page,
        "url": f"https://u.ae/{lang}/{page}",
        "lang": lang,
        "pair_url": None,
        "title": f"Title {page}",
        "text": "Heading\n" + "word " * 100,
        "snapshot_id": "2026-11-11",
    }


CHUNKS = [_chunk(0, "a"), _chunk(1, "a"), _chunk(0, "b"), _chunk(0, "c"), _chunk(0, "d")]


def _setup(monkeypatch, text):
    monkeypatch.setattr(pipeline, "retrieve", lambda q: {"final": [(i, 1.0) for i in range(5)]})
    monkeypatch.setattr(pipeline, "load_index", lambda: SimpleNamespace(chunks=CHUNKS))
    llm = LLMResult(text, 10, 5, 1.0, 0.001, "m")
    monkeypatch.setattr("arengov.generate.complete", lambda *a, **k: llm)


def test_answer_maps_citations(monkeypatch):
    _setup(monkeypatch, "Yes [3][5].")
    r = pipeline.answer([{"role": "user", "content": "how do I renew?"}])
    assert [c["n"] for c in r["citations"]] == [3, 5]
    assert r["citations"][0]["url"] == CHUNKS[2]["url"]
    assert r["citations"][0]["snippet"].endswith("…") and len(r["citations"][0]["snippet"]) <= 301
    assert r["lang"] == "en" and not r["refused"]


def test_refusal_distinct_pages_and_lang(monkeypatch):
    _setup(monkeypatch, "NO_ANSWER")
    r = pipeline.answer([{"role": "user", "content": "كيف أجدد؟"}])
    assert r["refused"] and r["refusal_reason"] == "no_answer" and r["lang"] == "ar"
    assert [c["n"] for c in r["citations"]] == [1, 2, 3]
    assert len({c["url"] for c in r["citations"]}) == 3
