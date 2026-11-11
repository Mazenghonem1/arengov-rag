from arengov import generate as g
from arengov.llm import LLMResult

CHUNKS = [
    {"lang": "en", "title": "T1", "url": "https://u.ae/en/a", "text": "A\nbody one"},
    {"lang": "ar", "title": "T2", "url": "https://u.ae/ar/b", "text": "B\nbody two"},
]


def test_parse_citations():
    text, ok, bad = g.parse_citations("x [1] y [٢] z [9] w [1]", 5)
    assert text == "x [1] y [2] z  w [1]"
    assert ok == [1, 2]
    assert bad == [9]


def test_build_prompt():
    system, msgs = g.build_prompt("q?", CHUNKS, "ar")
    content = msgs[0]["content"]
    assert system == g.SYSTEM_PROMPT
    assert "[1] (en) T1 - https://u.ae/en/a\nA\nbody one" in content
    assert "[2] (ar) T2" in content
    assert content.endswith("Question: q?\nAnswer language: Arabic")
    assert g.build_prompt("q", CHUNKS, "en")[1][0]["content"].endswith("Answer language: English")


def test_generate_no_answer(monkeypatch):
    fake = LLMResult("NO_ANSWER", 1, 1, 1.0, 0.0, "m")
    monkeypatch.setattr(g, "complete", lambda *a, **k: fake)
    out = g.generate("q", CHUNKS, "en")
    assert out["no_answer"] is True


def test_generate_cited(monkeypatch):
    fake = LLMResult("Fact [2][7].", 1, 1, 1.0, 0.0, "m")
    monkeypatch.setattr(g, "complete", lambda *a, **k: fake)
    out = g.generate("q", CHUNKS, "en")
    assert out["cited"] == [2] and out["invalid_citations"] == [7]
    assert out["answer"] == "Fact [2]."
