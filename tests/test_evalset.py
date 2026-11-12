import json
from collections import Counter

import pytest

from arengov import evalset

PAGE = "information-and-services/jobs/x"


@pytest.fixture(autouse=True)
def known_pages(monkeypatch):
    chunk = {"page_id": PAGE, "lang": "en", "category": "jobs"}
    monkeypatch.setattr(evalset, "load_index", lambda: type("I", (), {"chunks": [chunk]})())


def q(**kw):
    base = {
        "id": "q001",
        "lang": "en",
        "type": "single",
        "category": "jobs",
        "turns": ["How much?"],
        "gold_page_ids": [PAGE],
        "reference_answer": "100 AED.",
        "key_facts": ["100 AED", "paid online"],
        "answerable": True,
        "origin": "human",
        "notes": "",
    }
    return {**base, **kw}


def write(tmp_path, *qs):
    p = tmp_path / "q.jsonl"
    p.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in qs), "utf-8")
    return p


def test_valid_file_has_no_errors(tmp_path):
    assert evalset.validate(write(tmp_path, q())) == []


@pytest.mark.parametrize(
    "bad, fragment",
    [
        (q(id="x1"), "id must match"),
        (q(type="weird"), "type="),
        (q(lang="fr"), "lang="),
        (q(category="food"), "category="),
        (q(origin="bot"), "origin="),
        (q(split="val"), "split="),
        (q(answerable=False), "answerable"),
        (q(gold_page_ids=[]), "1-3 gold"),
        (q(gold_page_ids=["nope"]), "not in index"),
        (q(key_facts=["one"]), "2-4 key_facts"),
        (q(reference_answer=" "), "reference_answer is empty"),
        (q(turns=["a", "b"]), "needs 1-1 turns"),
        (q(type="multi_turn", turns=["a"]), "needs 2-3 turns"),
        (q(type="mixed_script"), "both Arabic and Latin"),
        (q(type="unanswerable_oos", answerable=False), "empty gold"),
        (q(turns="not a list"), "turns must be list"),
    ],
)
def test_validate_catches(tmp_path, bad, fragment):
    assert any(fragment in e for e in evalset.validate(write(tmp_path, bad)))


def test_validate_catches_bad_json_and_duplicate_ids(tmp_path):
    p = write(tmp_path, q(), q())
    p.write_text(p.read_text("utf-8") + "{oops\n", "utf-8")
    errors = evalset.validate(p)
    assert any("duplicate id" in e for e in errors)
    assert any("not valid JSON" in e for e in errors)


def test_mixed_script_ok(tmp_path):
    ok = q(type="mixed_script", turns=["كم رسوم الـ visa؟"], lang="ar")
    assert evalset.validate(write(tmp_path, ok)) == []


def _full_set():
    out, n = [], 0
    cats = iter(["visa-and-emirates-id", "jobs", "business"] * 12)
    for typ, per_lang in evalset.EXPECTED_PER_LANG.items():
        for lang in evalset.LANGS:
            for _ in range(per_lang):
                n += 1
                un = typ in evalset.UNANSWERABLE
                turns = (
                    ["a", "b"]
                    if typ == "multi_turn"
                    else ["مرحبا hello" if typ == "mixed_script" else "a"]
                )
                out.append(
                    q(
                        id=f"q{n:03d}",
                        lang=lang,
                        type=typ,
                        category=next(cats) if typ == "single" else "jobs",
                        turns=turns,
                        answerable=not un,
                        gold_page_ids=[] if un else [PAGE],
                        key_facts=[] if un else ["a", "b"],
                        reference_answer="" if un else "x",
                    )
                )
    return out


def test_assign_splits_and_strict(tmp_path):
    p = write(tmp_path, *_full_set())
    assert any("no split" in e for e in evalset.validate(p, strict=True))
    evalset.assign_splits(p)
    assert evalset.validate(p, strict=True) == []
    qs = [json.loads(line) for line in p.read_text("utf-8").splitlines()]
    assert [x["id"] for x in qs] == sorted(x["id"] for x in qs)
    assert Counter(x["split"] for x in qs) == {"dev": 40, "test": 20}
    groups = Counter((x["type"], x["lang"]) for x in qs)
    test = Counter((x["type"], x["lang"]) for x in qs if x["split"] == "test")
    for key, g in groups.items():
        assert test[key] in (g // 3, -(-g // 3))


def test_assign_splits_is_deterministic(tmp_path):
    a, b = write(tmp_path, *_full_set()), tmp_path / "b.jsonl"
    b.write_text(a.read_text("utf-8"), "utf-8")
    evalset.assign_splits(a)
    evalset.assign_splits(b)
    assert a.read_text("utf-8") == b.read_text("utf-8")


def test_strict_flags_wrong_counts(tmp_path):
    errors = evalset.validate(write(tmp_path, q()), strict=True)
    assert any("single/en: expected 18" in e for e in errors)
