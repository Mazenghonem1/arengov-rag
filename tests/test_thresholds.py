import json

import pytest

from arengov import eval_answers as E
from arengov.__main__ import main


@pytest.mark.parametrize("b,t", [(0.734, 0.65), (0.70, 0.65), (1.0, 0.95), (0.04, 0.0)])
def test_rule(b, t):
    assert E.threshold_for(b) == t


def _summary(tmp_path, name, kind, metrics, split="test"):
    p = tmp_path / name
    p.write_text(json.dumps({"kind": kind, "split": split, "metrics": metrics}))
    return p


def test_set_and_ratchet(tmp_path, monkeypatch):
    monkeypatch.setattr(E, "THRESHOLDS", tmp_path / "thresholds.json")
    r = _summary(tmp_path, "r.json", "retrieval", {"recall@5": 0.81, "mrr@10": 0.64})
    a = _summary(
        tmp_path,
        "a.json",
        "answers",
        {"refusal_correct": 0.9, "lang_match": 1.0, "faithfulness": 0.8, "citation_accuracy": None},
    )
    t = E.set_thresholds(r, a)
    assert t["retrieval"] == {"recall@5": 0.75, "mrr@10": 0.55}
    assert t["answers"] == {"refusal_correct": 0.85, "lang_match": 0.95, "faithfulness": 0.75}
    # a worse run must not lower anything; a better one raises
    r2 = _summary(tmp_path, "r2.json", "retrieval", {"recall@5": 0.6, "mrr@10": 0.9})
    t = E.set_thresholds(r2, a)
    assert t["retrieval"] == {"recall@5": 0.75, "mrr@10": 0.85}


def test_set_rejects_dev(tmp_path, monkeypatch):
    monkeypatch.setattr(E, "THRESHOLDS", tmp_path / "thresholds.json")
    r = _summary(tmp_path, "r.json", "retrieval", {"recall@5": 0.8}, split="dev")
    with pytest.raises(ValueError):
        E.set_thresholds(r, r)


def test_check_exit_codes(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(E, "THRESHOLDS", tmp_path / "thresholds.json")
    E.THRESHOLDS.write_text(json.dumps({"retrieval": {"recall@5": 0.75, "mrr@10": 0.55}}))
    good = _summary(tmp_path, "g.json", "retrieval", {"recall@5": 0.75, "mrr@10": 0.6})
    bad = _summary(tmp_path, "b.json", "retrieval", {"recall@5": 0.7, "mrr@10": 0.6})
    assert E.check_thresholds([good]) is True
    assert E.check_thresholds([good, bad]) is False
    assert "FAIL" in capsys.readouterr().out

    with pytest.raises(SystemExit) as e:
        main(["check-thresholds", str(good), str(bad)])
    assert e.value.code == 1
    main(["check-thresholds", str(good)])  # all pass: returns normally
