import logging
import re
import time
from dataclasses import dataclass
from functools import cache

from openai import OpenAI

from arengov import config

log = logging.getLogger(__name__)


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float
    model: str


@cache
def _client(backend):
    if backend == "ollama":
        return OpenAI(base_url=config.OLLAMA_BASE_URL, api_key="ollama", timeout=60)
    return OpenAI(timeout=60)


def complete(system, messages, max_tokens, *, role="gen", json_schema=None):
    # backend is read at call time so the CLI flag and tests can change it
    backend = "openai" if role == "judge" else config.LLM_BACKEND
    if backend == "ollama":
        model = config.OLLAMA_MODEL
        kwargs = {
            "messages": [{"role": "system", "content": system + "\n/no_think"}, *messages],
            "max_tokens": max_tokens,
        }
    else:
        model = config.JUDGE_MODEL if role == "judge" else config.GEN_MODEL
        kwargs = {
            "messages": [{"role": "system", "content": system}, *messages],
            "max_completion_tokens": max_tokens,
            "reasoning_effort": config.REASONING_EFFORT,
        }
    if json_schema:
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "result", "schema": json_schema, "strict": True},
        }
    t0 = time.perf_counter()
    resp = _client(backend).chat.completions.create(model=model, **kwargs)
    latency_ms = (time.perf_counter() - t0) * 1000
    choice = resp.choices[0]
    text = choice.message.content or ""
    if backend == "ollama":
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    if choice.finish_reason == "length":
        log.warning("LLM output hit max_tokens (%s)", max_tokens)
    n_in, n_out = resp.usage.prompt_tokens, resp.usage.completion_tokens
    p_in, p_out = config.PRICES_PER_M.get(model, (0, 0)) if backend == "openai" else (0, 0)
    return LLMResult(text, n_in, n_out, latency_ms, n_in * p_in / 1e6 + n_out * p_out / 1e6, model)
