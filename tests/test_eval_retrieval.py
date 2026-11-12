import json

from arengov import config, eval_retrieval, pipeline
from arengov.eval_retrieval import hit_at, rr_at


def test_hit_and_rr():
    pages = ["a", "b", "c", "d", "e", "f", "gold", "h"]
    assert hit_at(["gold", "x"], ["gold"], 5) and rr_at(["gold", "x"], ["gold"], 10) == 1
    assert not hit_at(pages, ["gold"], 5) and hit_at(pages, ["gold"], 10)
    assert rr_at(pages, ["gold"], 5) == 0 and rr_at(pages, ["gold"], 10) == 1 / 7
    assert not hit_at(pages, ["zzz"], 10) and rr_at(pages, ["zzz"], 10) == 0
    assert rr_at(["a", "gold", "gold"], ["gold"], 10) == 0.5  # first occurrence counts


def test_run(tmp_path, monkeypatch):
    def q(i, t, lang, gold, split="dev"):
        return {"id": i, "type": t, "lang": lang, "turns": ["x", f"query {i}"],
                "gold_page_ids": gold, "split": split}  # fmt: skip

    qs = [
        q("q1", "single", "en", ["A"]),
        q("q2", "multi_turn", "ar", ["B"]),
        q("q3", "unanswerable_oos", "en", []),
        q("q4", "single", "en", ["A"], "test"),
    ]
    (tmp_path / "questions.jsonl").write_text("\n".join(json.dumps(x) for x in qs), "utf-8")
    (tmp_path / "index_version.txt").write_text("v1\n")
    monkeypatch.setattr(config, "EVAL_DIR", tmp_path)
    monkeypatch.setattr(config, "INDEX_VERSION_FILE", tmp_path / "index_version.txt")
    monkeypatch.setattr(eval_retrieval, "RESULTS_MD", tmp_path / "results.md")
    chunks = [{"page_id": p} for p in "ABCDEFG"]
    monkeypatch.setattr(eval_retrieval, "load_index", lambda: type("I", (), {"chunks": chunks})())
    seen = []

    def fake(query, **kw):
        seen.append((query, kw["lang_filter"]))
        order = [0, 1, 2, 3, 4, 5, 6] if query == "query q1" else [2, 3, 4, 5, 6, 0, 1]
        ranked = [(i, 1.0) for i in order]
        return {"candidates": ranked[:20], "ranked": ranked, "final": ranked[:5]}

    monkeypatch.setattr(pipeline, "retrieve", fake)
    s = eval_retrieval.run("dev", label="t", cross_lingual=True, record=True)
    assert s["n"] == 2  # q3 unanswerable, q4 is test
    assert seen == [("query q1", "ar"), ("query q2", "en")]  # last turn, opposite language
    # q1: gold at rank 1; q2: gold at rank 7 (outside top 5, inside top 10)
    assert s["metrics"]["recall@5"] == 0.5 and s["metrics"]["recall@20"] == 1.0
    assert abs(s["metrics"]["mrr@10"] - (1 + 1 / 7) / 2) < 1e-9
    assert s["by_lang"]["ar"]["recall@5"] == 0.0
    assert (tmp_path / "results.md").read_text().count("|") > 20
