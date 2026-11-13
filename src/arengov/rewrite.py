# ruff: noqa: E501  (prompt text is fixed by the phase file)
from arengov import config
from arengov.llm import complete

REWRITE_SYSTEM = """You rewrite a follow-up question into one standalone question for a search engine about UAE government services.
Use the earlier questions only to resolve references such as "it", "that visa" or "and for my wife?".
Keep the language of the follow-up question. Keep names of visas, permits and documents exactly as written.
If the follow-up is already standalone, return it unchanged.
Reply with the standalone question only."""


def rewrite(prev_user_msgs, question, lang):
    # lang is unused: the system prompt already says "keep the follow-up's language"
    prev = prev_user_msgs[-config.HISTORY_MAX_TURNS :]
    earlier = "\n".join(f"{i}. {m}" for i, m in enumerate(prev, 1))
    content = f"Earlier questions:\n{earlier}\nFollow-up question: {question}"
    res = complete(
        REWRITE_SYSTEM, [{"role": "user", "content": content}], config.REWRITE_MAX_TOKENS
    )
    return (res.text.strip() or question), res
