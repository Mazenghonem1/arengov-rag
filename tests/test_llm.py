from types import SimpleNamespace

from arengov import config, llm


class FakeClient:
    def __init__(self, text):
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.text = text

    def _create(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=self.text), finish_reason="stop")
            ],
            usage=SimpleNamespace(prompt_tokens=1000, completion_tokens=200),
        )


def _patch(monkeypatch, backend, text="ok"):
    fake = FakeClient(text)
    used = []
    monkeypatch.setattr(llm, "_client", lambda b: used.append(b) or fake)
    monkeypatch.setattr(config, "LLM_BACKEND", backend)
    return fake, used


def test_ollama_strips_think_and_adds_no_think(monkeypatch):
    fake, _ = _patch(monkeypatch, "ollama", "<think>\nhmm\n</think>\nanswer")
    r = llm.complete("sys", [{"role": "user", "content": "hi"}], 50)
    assert r.text == "answer"
    assert fake.calls[0]["messages"][0]["content"] == "sys\n/no_think"
    assert r.cost_usd == 0


def test_judge_uses_openai_even_with_ollama_backend(monkeypatch):
    fake, used = _patch(monkeypatch, "ollama")
    r = llm.complete("sys", [], 50, role="judge")
    assert used == ["openai"]
    assert fake.calls[0]["model"] == config.JUDGE_MODEL
    assert fake.calls[0]["reasoning_effort"] == config.REASONING_EFFORT
    assert r.cost_usd == 1000 * 1.00 / 1e6 + 200 * 5.00 / 1e6


def test_json_schema_response_format(monkeypatch):
    fake, _ = _patch(monkeypatch, "openai")
    llm.complete("s", [], 50, json_schema={"type": "object"})
    rf = fake.calls[0]["response_format"]
    assert rf["json_schema"]["strict"] is True
