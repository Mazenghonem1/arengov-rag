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
