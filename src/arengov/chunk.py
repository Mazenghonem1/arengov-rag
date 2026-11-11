import re
from functools import cache

from tokenizers import Tokenizer

from arengov.config import CHUNK_MAX_TOKENS, TOKENIZER_MODEL


@cache
def _tok() -> Tokenizer:
    return Tokenizer.from_pretrained(TOKENIZER_MODEL)


def count_tokens(text: str) -> int:
    return len(_tok().encode(text, add_special_tokens=False).ids)


def _split_long(para: str, fits) -> list[str]:
    """Split a paragraph that doesn't fit alone: sentences first, then word groups."""
    pieces: list[str] = []
    for sent in re.split(r"(?<=[.!?؟])\s+", para):
        if fits(sent):
            pieces.append(sent)
            continue
        group: list[str] = []
        for w in sent.split():
            if group and not fits(" ".join([*group, w])):
                pieces.append(" ".join(group))
                group = []
            group.append(w)
        if group:
            pieces.append(" ".join(group))
    return pieces


def _pack(heading_path: str, paras: list[str]) -> list[str]:
    def fits(parts):
        return count_tokens(heading_path + "\n" + "\n\n".join(parts)) <= CHUNK_MAX_TOKENS

    units: list[str] = []
    for p in paras:
        units += [p] if fits([p]) else _split_long(p, lambda s: fits([s]))
    bodies: list[str] = []
    cur: list[str] = []
    for u in units:
        if cur and not fits([*cur, u]):
            bodies.append("\n\n".join(cur))
            # one paragraph of overlap, unless it would crowd out the new paragraph
            cur = [cur[-1]] if fits([cur[-1], u]) else []
        cur.append(u)
    if cur:
        bodies.append("\n\n".join(cur))
    return bodies


def chunk_page(title: str, markdown: str, meta: dict) -> list[dict]:
    # sections: (h2, h3, [paragraphs]) in document order
    sections: list[tuple[str, str, list[str]]] = [("", "", [])]
    h2 = h3 = ""
    for block in markdown.split("\n\n"):
        if block.startswith("# "):
            continue  # H1: the title covers it
        if block.startswith("## "):
            h2, h3 = block[3:].strip(), ""
            sections.append((h2, h3, []))
        elif block.startswith("### "):
            h3 = block[4:].strip()
            sections.append((h2, h3, []))
        elif block.strip():
            sections[-1][2].append(block)  # includes H4+ as plain text

    chunks: list[dict] = []
    for h2, h3, paras in sections:
        if not paras:
            continue
        path = " > ".join(x for x in (title, h2, h3) if x)
        for body in _pack(path, paras):
            chunks.append(
                {
                    "chunk_id": f"{meta['lang']}:{meta['page_id']}:{len(chunks)}",
                    "page_id": meta["page_id"],
                    "url": meta["url"],
                    "lang": meta["lang"],
                    "pair_url": meta["pair_url"],
                    "title": title,
                    "heading_path": path,
                    "text": path + "\n" + body,
                    "snapshot_id": meta["snapshot_id"],
                    "category": meta["category"],
                }
            )
    return chunks
