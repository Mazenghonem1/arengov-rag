import json

import pytest

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


def test_export_blind(tmp_path):
    det = tmp_path / "eval" / "details"
    det.mkdir(parents=True)
    (tmp_path / "eval" / "a.json").write_text(json.dumps({"index_version": "v"}))
    ok = {k: {"reason": "SECRETREASON", "pass": k != "correctness"} for k in J.CRITERIA}
    rows = [
        {
            "id": "q1",
            "answerable": True,
            "refused": False,
            "error": None,
            "answer": "A1 [1]",
            "final_chunk_ids": ["c1"],
            "judge": ok,
        },
        {
            "id": "q2",
            "answerable": True,
            "refused": True,
            "error": None,
            "answer": "no",
            "final_chunk_ids": [],
            "judge": None,
        },
        {
            "id": "q3",
            "answerable": False,
            "refused": False,
            "error": None,
            "answer": "x",
            "final_chunk_ids": [],
            "judge": None,
        },
    ]
    (det / "a.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    qs = {
        i: {"id": i, "split": "dev", "turns": ["Q?"], "reference_answer": "R", "key_facts": ["f"]}
        for i in ("q1", "q2", "q3")
    }
    out = tmp_path / "g"
    n = J.export_blind([det / "a.jsonl"], out, questions=qs, chunks_by_id={"c1": CHUNKS[0]})
    assert n == 1
    md = (out / "items.md").read_text("utf-8")
    assert (
        "## Item 1" in md and "A1 [1]" in md and "SECRETREASON" not in md and "faithfulness:" in md
    )
    key = json.loads((out / "key.json").read_text("utf-8"))
    assert key["1"]["q_id"] == "q1" and key["1"]["judge"]["correctness"] is False
    assert (out / "grades.csv").read_text().splitlines()[1] == "1,,,,"


def test_kappa_textbook():
    assert J.kappa(20, 5, 10, 15) == pytest.approx(0.40)  # po 0.70, pe 0.50


def test_kappa_all_same_label_is_none():
    assert J.kappa(10, 0, 0, 0) is None


def test_agreement(tmp_path):
    key = {
        str(i): {
            "q_id": f"q{i}",
            "split": "dev" if i < 3 else "test",
            "judge": {c: i != 1 for c in J.CRITERIA},
        }
        for i in (1, 2, 3, 4)
    }
    (tmp_path / "k.json").write_text(json.dumps(key))
    (tmp_path / "g.csv").write_text(
        "item_id,faithfulness,correctness,citation_accuracy,note\n"
        + "".join(f"{i},1,1,1,\n" for i in (1, 2, 3, 4))
    )
    r = J.agreement(tmp_path / "g.csv", tmp_path / "k.json")["faithfulness"]
    assert r["n"] == 4 and r["agreement"] == 0.75 and r["disagreements"] == ["q1"]
    assert r["confusion"] == {"jp_hp": 3, "jp_hf": 0, "jf_hp": 1, "jf_hf": 0}
    assert r["dev"]["n"] == 2 and r["test"]["agreement"] == 1.0


def test_agreement_rejects_blank(tmp_path):
    (tmp_path / "k.json").write_text(
        json.dumps({"1": {"q_id": "q1", "split": "dev", "judge": {c: True for c in J.CRITERIA}}})
    )
    (tmp_path / "g.csv").write_text(
        "item_id,faithfulness,correctness,citation_accuracy,note\n1,1,,1,\n"
    )
    with pytest.raises(ValueError, match="correctness"):
        J.agreement(tmp_path / "g.csv", tmp_path / "k.json")
