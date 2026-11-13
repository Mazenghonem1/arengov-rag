# ruff: noqa: E501  (JUDGE_SYSTEM must stay verbatim from the phase file)
import json

from arengov import config
from arengov.llm import complete

JUDGE_SYSTEM = """You grade one answer from a question-answering system about UAE government services.
You get the user's question, the numbered sources the system was given, the system's answer, a reference answer and key facts written by a human expert.
Grade three criteria, each strictly pass or fail:
- faithfulness: pass if every factual statement in the answer is supported by the numbered sources. Fail if any statement is unsupported by them, even if it is true in the real world.
- correctness: pass if the answer contains every key fact (any wording, any language) and nothing in it contradicts the reference answer. Fail otherwise.
- citation_accuracy: pass if every bracketed citation [n] points to a source that supports the sentence it is attached to. Fail if any citation points to a source that does not support its sentence.
Answers and sources may be in Arabic or English; judge meaning, not language.
For each criterion write a one-sentence reason first, then the verdict."""

CRITERIA = ("faithfulness", "correctness", "citation_accuracy")

_VERDICT = {
    "type": "object",
    "properties": {"reason": {"type": "string"}, "pass": {"type": "boolean"}},
    "required": ["reason", "pass"],
    "additionalProperties": False,
}
JUDGE_SCHEMA = {
    "type": "object",
    "properties": {k: _VERDICT for k in CRITERIA},
    "required": list(CRITERIA),
    "additionalProperties": False,
}


def build_message(question, chunks, answer, reference_answer, key_facts, earlier_turns=()):
    lines = []
    if earlier_turns:
        lines.append("Earlier user messages: " + " | ".join(earlier_turns))
    lines += [f"Question: {question}", "Sources:"]
    for i, c in enumerate(chunks, 1):
        lines += [f"[{i}] ({c['lang']}) {c['title']} - {c['url']}", c["text"]]
    lines += ["Answer:", answer, "Reference answer:", reference_answer, "Key facts:"]
    lines += [f"- {f}" for f in key_facts]
    return "\n".join(lines)


def judge(question, chunks, answer, reference_answer, key_facts, earlier_turns=()):
    msg = build_message(question, chunks, answer, reference_answer, key_facts, earlier_turns)
    res = complete(
        JUDGE_SYSTEM,
        [{"role": "user", "content": msg}],
        config.JUDGE_MAX_TOKENS,
        role="judge",
        json_schema=JUDGE_SCHEMA,
    )
    return json.loads(res.text) | {"cost_usd": res.cost_usd}


def export_blind(details_paths, out_dir="eval/grading", seed=7, questions=None, chunks_by_id=None):
    """Write a blind grading sheet (no judge output in items.md) plus the key to unblind it."""
    import random
    from pathlib import Path

    from arengov.eval_answers import _questions
    from arengov.index import load_index

    qs = questions or {q["id"]: q for q in _questions("all")}
    items = []
    for p in map(Path, details_paths):
        summary = json.loads((p.parent.parent / (p.stem + ".json")).read_text("utf-8"))
        by_id = chunks_by_id or {
            c["chunk_id"]: c for c in load_index(summary["index_version"]).chunks
        }
        for line in p.read_text("utf-8").splitlines():
            r = json.loads(line) if line.strip() else None
            if r and r["answerable"] and not r["refused"] and not r["error"]:
                items.append((r, qs[r["id"]], [by_id[c] for c in r["final_chunk_ids"]], str(p)))
    random.Random(seed).shuffle(items)

    rubric = JUDGE_SYSTEM.split("\n", 3)[3].rsplit("\n", 2)[0]  # the 3 criteria + language line
    md = [
        "# Blind grading",
        "",
        "Enter 1 (pass) or 0 (fail) per criterion in grades.csv.",
        "",
        rubric,
    ]
    key = {}
    for i, (r, q, chunks, path) in enumerate(items, 1):
        msg = build_message(
            q["turns"][-1],
            chunks,
            r["answer"],
            q["reference_answer"],
            q["key_facts"],
            q["turns"][:-1],
        )
        md += ["", f"## Item {i}", "", "```text", msg, "```"]
        key[i] = {
            "q_id": q["id"],
            "split": q["split"],
            "details_path": path,
            "judge": {k: r["judge"][k]["pass"] for k in CRITERIA},
        }
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "items.md").write_text("\n".join(md) + "\n", "utf-8")
    (out / "grades.csv").write_text(
        "item_id,faithfulness,correctness,citation_accuracy,note\n"
        + "".join(f"{i},,,,\n" for i in key),
        "utf-8",
    )
    (out / "key.json").write_text(json.dumps(key, indent=2, ensure_ascii=False) + "\n", "utf-8")
    return len(items)
