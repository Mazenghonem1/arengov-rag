import json

from arengov import judge as J

CHUNKS = [{"lang": "en", "title": "T1", "url": "http://u/1", "text": "Body one"}]
VERDICT = {"reason": "ok", "pass": True}
GOOD = {k: VERDICT for k in J.CRITERIA}


def test_message_format():
    m = J.build_message("Q?", CHUNKS, "Ans [1]", "Ref", ["f1", "f2"], ["earlier a", "earlier b"])
    assert m == (
        "Earlier user messages: earlier a | earlier b\nQuestion: Q?\nSources:\n"
        "[1] (en) T1 - http://u/1\nBody one\nAnswer:\nAns [1]\nReference answer:\nRef\n"
        "Key facts:\n- f1\n- f2"
    )
    assert "Earlier" not in J.build_message("Q?", CHUNKS, "A", "R", [])


def test_judge_parses_and_adds_cost(monkeypatch):
    seen = {}

    def fake(system, messages, max_tokens, *, role, json_schema):
        seen.update(role=role, schema=json_schema, system=system)
        return type("R", (), {"text": json.dumps(GOOD), "cost_usd": 0.004})()

    monkeypatch.setattr(J, "complete", fake)
    r = J.judge("Q?", CHUNKS, "A", "R", ["f"])
    assert r["faithfulness"]["pass"] is True and r["cost_usd"] == 0.004
    assert seen["role"] == "judge" and seen["schema"] is J.JUDGE_SCHEMA
    assert seen["system"] == J.JUDGE_SYSTEM


def test_schema_is_strict_everywhere():
    s = J.JUDGE_SCHEMA
    assert s["additionalProperties"] is False and set(s["required"]) == set(J.CRITERIA)
    for v in s["properties"].values():
        assert v["additionalProperties"] is False and set(v["required"]) == {"reason", "pass"}
