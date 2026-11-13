from arengov import rewrite as rw
from arengov.llm import LLMResult


def _fake(text, seen):
    def complete(system, messages, max_tokens):
        seen.append(messages[0]["content"])
        return LLMResult(text, 1, 1, 1.0, 0.0, "m")

    return complete


def test_prompt_has_only_last_three_previous(monkeypatch):
    seen = []
    monkeypatch.setattr(rw, "complete", _fake("standalone?", seen))
    text, _ = rw.rewrite(["q1", "q2", "q3", "q4"], "and for my wife?", "en")
    assert text == "standalone?"
    assert (
        seen[0] == "Earlier questions:\n1. q2\n2. q3\n3. q4\nFollow-up question: and for my wife?"
    )


def test_empty_output_falls_back(monkeypatch):
    monkeypatch.setattr(rw, "complete", _fake("  ", []))
    assert rw.rewrite(["q1"], "and for her?", "en")[0] == "and for her?"
