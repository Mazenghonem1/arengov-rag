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


def kappa(jp_hp, jp_hf, jf_hp, jf_hf):
    """Cohen's kappa from confusion counts; None when chance agreement is 1 (all one label)."""
    n = jp_hp + jp_hf + jf_hp + jf_hf
    po = (jp_hp + jf_hf) / n
    pj, ph = (jp_hp + jp_hf) / n, (jp_hp + jf_hp) / n
    pe = pj * ph + (1 - pj) * (1 - ph)
    return None if pe == 1 else (po - pe) / (1 - pe)


def _stats(pairs):
    """pairs: [(q_id, judge_bool, human_bool)]"""
    c = {"jp_hp": 0, "jp_hf": 0, "jf_hp": 0, "jf_hf": 0}
    for _, j, h in pairs:
        c[f"j{'p' if j else 'f'}_h{'p' if h else 'f'}"] += 1
    n = len(pairs)
    return {
        "n": n,
        "agreement": (c["jp_hp"] + c["jf_hf"]) / n if n else None,
        "kappa": kappa(**c) if n else None,
        "confusion": c,
        "judge_pass": c["jp_hp"] + c["jp_hf"],
        "human_pass": c["jp_hp"] + c["jf_hp"],
        "disagreements": [q for q, j, h in pairs if j != h],
    }


def agreement(grades_csv, key_json):
    """Per criterion (overall, dev, test): n, agreement, kappa, confusion, disagreements."""
    import csv
    from pathlib import Path

    key = json.loads(Path(key_json).read_text("utf-8"))
    rows = {r["item_id"]: r for r in csv.DictReader(Path(grades_csv).open(encoding="utf-8"))}
    bad = [
        f"item {i}: {c}={rows.get(i, {}).get(c)!r}"
        for i in key
        for c in CRITERIA
        if rows.get(i, {}).get(c, "").strip() not in ("0", "1")
    ]
    if bad:
        raise ValueError("grades must be 0/1 for every item; problems: " + "; ".join(bad))
    out = {}
    for c in CRITERIA:
        pairs = [
            (key[i]["split"], key[i]["q_id"], key[i]["judge"][c], rows[i][c].strip() == "1")
            for i in key
        ]
        out[c] = _stats([p[1:] for p in pairs]) | {
            s: _stats([p[1:] for p in pairs if p[0] == s]) for s in ("dev", "test")
        }
    return out


def record_agreement(
    label, grades="eval/grading/grades.csv", key="eval/grading/key.json", record=False
):
    """Run agreement(), print a table, write eval/results/<ts>_judge-agreement_<label>.json."""
    from datetime import datetime

    from arengov.eval_retrieval import RESULTS_MD

    res = agreement(grades, key)
    now = datetime.now()
    out = config.EVAL_DIR / "results" / f"{now:%Y%m%d-%H%M}_judge-agreement_{label}.json"
    out.write_text(
        json.dumps(
            {"label": label, "timestamp": now.isoformat(timespec="seconds"), "criteria": res},
            indent=2,
        )
        + "\n",
        "utf-8",
    )
    pct = lambda v: "—" if v is None else f"{v:.0%}"  # noqa: E731
    kap = lambda v: "undefined" if v is None else f"{v:.2f}"  # noqa: E731
    lines = []
    for c, r in res.items():
        for part, s in (("all", r), ("dev", r["dev"]), ("test", r["test"])):
            print(
                f"{c:<18}{part:<5}n={s['n']:<3}agree={pct(s['agreement']):<5}kappa={kap(s['kappa']):<10}{s['confusion']}"
            )
        lines.append(
            f"| {now:%Y-%m-%d} | {label} | {c} | {r['n']} | {pct(r['agreement'])} | {kap(r['kappa'])} | {r['judge_pass']} / {r['human_pass']} |\n"
        )
    if record:
        text = RESULTS_MD.read_text("utf-8")
        if "## Judge validation" not in text:
            text += "\n## Judge validation\n\n| date | label | criterion | n | agreement | κ | judge pass / human pass |\n|---|---|---|---|---|---|---|\n"
        RESULTS_MD.write_text(text + "".join(lines), "utf-8")
    return res
