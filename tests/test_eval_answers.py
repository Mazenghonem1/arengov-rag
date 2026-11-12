import json
from types import SimpleNamespace

from arengov import config, eval_answers, llm, pipeline
from arengov.__main__ import main
from arengov.eval_answers import det_checks

Q = {"answerable": True, "lang": "en"}
UQ = {"answerable": False, "lang": "ar"}
CRIT = ("faithfulness", "correctness", "citation_accuracy")
GOOD = {k: {"reason": "r", "pass": True} for k in CRIT}
CHUNK = {"lang": "en", "title": "T", "url": "u", "text": "x", "chunk_id": "en:p:0"}


def out(answer="Fee is AED 20 [1].", refused=False, cites=1, invalid=()):
    return {
        "answer": answer,
        "refused": refused,
        "citations": [{"n": i} for i in range(cites)],
        "invalid_citations": list(invalid),
    }


def test_refusal_correct_combos():
    assert det_checks(Q, out())["refusal_correct"] is True
    assert det_checks(Q, out(refused=True, cites=0))["refusal_correct"] is False
    assert det_checks(UQ, out("لا أعرف", refused=True))["refusal_correct"] is True
    assert det_checks(UQ, out("جواب [1]"))["refusal_correct"] is False


def test_lang_match_ignores_markers_and_urls():
    # the Arabic URL and the markers must not tip the detector away from English
    c = det_checks(Q, out("See https://u.ae/ar/خدمات/الإقامة [1][2] the fee is twenty dirhams [3]"))
    assert c["lang_match"] is True
    assert det_checks(Q, out("الرسوم عشرون درهماً [1]"))["lang_match"] is False
    assert det_checks(UQ, out("لم أجد الإجابة في الصفحات", refused=True, cites=0))["lang_match"]


def test_citation_valid():
    assert det_checks(Q, out())["citation_valid"] is True
    assert det_checks(Q, out(cites=0))["citation_valid"] is False
    assert det_checks(Q, out(invalid=[7]))["citation_valid"] is False
    assert det_checks(Q, out(refused=True, cites=0))["citation_valid"] is None  # answered only


def _env(tmp_path, monkeypatch):
    def q(i, turns, ans=True, t="single"):
        return {"id": i, "lang": "en", "type": t, "answerable": ans, "split": "dev",
                "turns": turns, "reference_answer": "R" if ans else "",
                "key_facts": ["f"] if ans else []}  # fmt: skip

    qs = [q("q1", ["a", "b"]), q("q2", ["boom"]), q("q3", ["c"], False, "unanswerable_oos")]
    (tmp_path / "questions.jsonl").write_text("\n".join(map(json.dumps, qs)), "utf-8")
    (tmp_path / "index_version.txt").write_text("v1\n")
    monkeypatch.setattr(config, "EVAL_DIR", tmp_path)
    monkeypatch.setattr(config, "INDEX_VERSION_FILE", tmp_path / "index_version.txt")
    monkeypatch.setattr(eval_answers, "RESULTS_MD", tmp_path / "results.md")
    monkeypatch.setattr(config, "LLM_BACKEND", "ollama")  # monkeypatch restores the originals
    monkeypatch.setattr(config, "JUDGE_MODEL", config.JUDGE_MODEL)

    def fake_answer(messages, lang):
        text = messages[-1]["content"]
        if text == "boom":
            raise RuntimeError("api down")
        refused = text == "c"
        return {
            "answer": "I couldn't find it." if refused else "Fee [1].",
            "citations": [] if refused else [{"n": 1, "url": "u", "title": "T"}],
            "refused": refused, "invalid_citations": [], "final_chunk_ids": ["en:p:0"],
            "latency_ms": 10.0, "usage": {"cost_usd": 0.001}, "_chunks": [CHUNK],
        }  # fmt: skip

    monkeypatch.setattr(pipeline, "answer", fake_answer)


def test_run_counts_errors_and_judges_only_answered(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch)
    monkeypatch.setattr(eval_answers, "judge", lambda *a: GOOD | {"cost_usd": 0.004})
    s = eval_answers.run("dev", label="t", record=True)
    assert config.LLM_BACKEND == "openai" and s["backend"] == "openai"
    assert s["n"] == 3 and s["errors"] == 1 and s["n_judged"] == 1
    m = s["metrics"]
    assert m["faithfulness"] == 0.5  # q1 pass, errored q2 fails; unanswerable q3 not judged
    assert m["refusal_correct"] == 2 / 3 and m["citation_valid"] == 0.5
    assert abs(s["eval_cost_usd"] - 0.004) < 1e-9
    assert (tmp_path / "results.md").read_text().count("|") > 20


def test_rejudge_replaces_only_judge(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch)
    monkeypatch.setattr(eval_answers, "judge", lambda *a: GOOD | {"cost_usd": 0.004})
    s = eval_answers.run("dev", label="t")
    details = next((tmp_path / "results" / "details").glob("*_answers_t_dev.jsonl"))
    bad = {k: {"reason": "r", "pass": False} for k in CRIT}
    monkeypatch.setattr(eval_answers, "judge", lambda *a: bad | {"cost_usd": 0.002})
    monkeypatch.setattr(eval_answers, "load_index", lambda v: SimpleNamespace(chunks=[CHUNK]))
    s2 = eval_answers.rejudge(details, "other-judge")
    assert s2["label"] == "t-rejudge-other-judge" and s2["judge_model"] == "other-judge"
    assert s2["metrics"]["faithfulness"] == 0.0
    assert s2["metrics"]["latency_p50_ms"] == s["metrics"]["latency_p50_ms"]
    assert s2["metrics"]["refusal_correct"] == s["metrics"]["refusal_correct"]


def test_cli_backend_defaults_to_openai_and_judge_model_reaches_llm(tmp_path, monkeypatch):
    _env(tmp_path, monkeypatch)
    seen = []

    def create(**kw):
        seen.append(kw["model"])
        msg = SimpleNamespace(content=json.dumps(GOOD))
        return SimpleNamespace(
            choices=[SimpleNamespace(message=msg, finish_reason="stop")],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=10),
        )

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm, "_client", lambda backend: client)
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    main(["eval-answers", "--split", "dev", "--label", "t", "--judge-model", "my-judge"])
    assert config.LLM_BACKEND == "openai"  # env said ollama; the flag default won
    assert seen == ["my-judge"]
    summary = next((tmp_path / "results").glob("*_answers_t_dev.json"))
    assert json.loads(summary.read_text("utf-8"))["judge_model"] == "my-judge"
