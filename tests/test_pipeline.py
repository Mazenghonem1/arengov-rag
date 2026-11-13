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


TOP = None


def _setup(monkeypatch, text):
    monkeypatch.setattr(
        pipeline, "retrieve", lambda q: {"final": [(i, 1.0) for i in range(5)], "top_score": TOP}
    )
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


def test_gate_refuses_without_llm(monkeypatch):
    _setup(monkeypatch, "Yes [1].")
    called = []
    monkeypatch.setattr(pipeline, "generate", lambda *a: called.append(1))
    monkeypatch.setattr(pipeline.config, "GATE_TAU", 0.5)
    monkeypatch.setattr(
        pipeline, "retrieve", lambda q: {"final": [(0, 1.0), (2, 1.0)], "top_score": 0.1}
    )
    r = pipeline.answer([{"role": "user", "content": "how do I renew?"}])
    assert r["refused"] and r["refusal_reason"] == "gate" and not called
    assert r["usage"]["cost_usd"] == 0 and len(r["citations"]) == 2


def test_gate_passes_above_tau(monkeypatch):
    _setup(monkeypatch, "Yes [1].")
    monkeypatch.setattr(pipeline.config, "GATE_TAU", 0.5)
    monkeypatch.setattr(pipeline, "retrieve", lambda q: {"final": [(0, 1.0)], "top_score": 0.9})
    r = pipeline.answer([{"role": "user", "content": "how do I renew?"}])
    assert not r["refused"]


def _spy(monkeypatch):
    _setup(monkeypatch, "Yes [1].")
    seen = {}
    monkeypatch.setattr(
        pipeline,
        "retrieve",
        lambda q: seen.setdefault("q", q) and {"final": [(0, 1.0)], "top_score": TOP},
    )
    return seen


def test_single_message_skips_rewrite(monkeypatch):
    seen = _spy(monkeypatch)
    monkeypatch.setattr(pipeline, "rewrite", lambda *a: 1 / 0)
    pipeline.answer([{"role": "user", "content": "how do I renew?"}])
    assert seen["q"] == "how do I renew?"


def test_history_is_rewritten_and_lang_is_original(monkeypatch):
    seen = _spy(monkeypatch)
    calls = []

    def fake_rewrite(prev, q, lang):
        calls.append((prev, q, lang))
        return "renew the golden visa", LLMResult("x", 3, 2, 1.0, 0.002, "m")

    monkeypatch.setattr(pipeline, "rewrite", fake_rewrite)
    msgs = [
        {"role": "user", "content": "golden visa?"},
        {"role": "assistant", "content": "long answer"},
        {"role": "user", "content": "وماذا عن تجديدها؟"},
    ]
    r = pipeline.answer(msgs)
    assert calls == [(["golden visa?"], "وماذا عن تجديدها؟", "ar")]
    assert seen["q"] == r["rewritten_query"] == "renew the golden visa"
    assert r["lang"] == "ar" and r["usage"]["cost_usd"] >= 0.002
