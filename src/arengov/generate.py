# ruff: noqa: E501  (SYSTEM_PROMPT must stay verbatim from the phase file)
import logging
import re

from arengov import config
from arengov.llm import complete

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You answer questions about UAE government services using only the numbered sources in the user message.
Rules:
1. Use only facts stated in the sources. If the sources do not contain the answer, reply with exactly: NO_ANSWER
2. After every sentence that states a fact, cite its source number in square brackets, like [2]. Use several, like [1][3], when needed. Cite only numbers that exist.
3. Write the whole answer in the language named on the last line of the user message, even when the sources are in another language. Write Arabic in Modern Standard Arabic.
4. Be concise: at most about 150 words. Use a short list for steps or required documents.
5. Add nothing that is not in the sources: no advice, no opinions, no outside knowledge."""

REFUSAL = {
    "en": "I couldn't find the answer in the u.ae pages I have. These pages may be related:",
    "ar": "لم أجد الإجابة في صفحات u.ae المتوفرة لدي. قد تكون هذه الصفحات ذات صلة:",
}

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_CITE = re.compile(r"\[([0-9٠-٩]+)\]")


def build_prompt(question, chunks, answer_lang):
    blocks = [
        f"[{i}] ({c['lang']}) {c['title']} - {c['url']}\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    ]
    lang_name = "Arabic" if answer_lang == "ar" else "English"
    content = (
        "Sources:\n"
        + "\n\n".join(blocks)
        + f"\n\nQuestion: {question}\nAnswer language: {lang_name}"
    )
    return SYSTEM_PROMPT, [{"role": "user", "content": content}]


def parse_citations(text, n):
    valid, invalid = set(), set()

    def fix(m):
        k = int(m.group(1).translate(_DIGITS))
        if 1 <= k <= n:
            valid.add(k)
            return f"[{k}]"
        invalid.add(k)
        return ""

    clean = _CITE.sub(fix, text)
    return clean, sorted(valid), sorted(invalid)


def refusal_message(lang):
    return REFUSAL[lang]


def generate(question, chunks, answer_lang):
    system, messages = build_prompt(question, chunks, answer_lang)
    llm = complete(system, messages, config.GEN_MAX_TOKENS)
    no_answer = "NO_ANSWER" in llm.text
    answer, cited, invalid = parse_citations(llm.text, len(chunks))
    if invalid:
        log.warning("removed out-of-range citations %s", invalid)
    return {
        "answer": answer,
        "cited": cited,
        "invalid_citations": invalid,
        "no_answer": no_answer,
        "llm": llm,
    }
