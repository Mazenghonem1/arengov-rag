import re

from bs4 import BeautifulSoup

# Found by inspecting real u.ae pages (phase 02): all 288 pages have exactly one of these.
CONTENT_SELECTOR = "main#mainContentContainer"
DROP_SELECTORS = [
    "script", "style", "noscript", "svg", "iframe", "ins",
    "form", "select", "button",  # feedback widget and the other forms
    ".topic-navigation",  # prev/next topic links
    ".artical-info-link",  # "last updated" date line (sic, u.ae's spelling)
]  # fmt: skip

_BLOCKS = ["h1", "h2", "h3", "h4", "p", "li", "table"]


def _text(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()


def _table(table) -> list[str]:
    rows = [[_text(c) for c in tr.find_all(["th", "td"])] for tr in table.find_all("tr")]
    rows = [r for r in rows if any(r)]
    if not rows:
        return []
    if table.find("tr").find("th"):
        head, rows = rows[0], rows[1:]
        return ["; ".join(f"{h}: {v}" for h, v in zip(head, r, strict=False)) for r in rows]
    return [" | ".join(r) for r in rows]


def clean_html(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.title.get_text() if soup.title else ""
    for sel in DROP_SELECTORS:
        for el in soup.select(sel):
            el.decompose()
    box = soup.select_one(CONTENT_SELECTOR)
    if box is None:
        return "", ""
    h1 = box.find("h1")
    # <title> is "Page | The Official Portal ..."; the part before the last " | " is the page name.
    title = _text(h1) if h1 else title_tag.rsplit("|", 1)[0].strip()

    blocks: list[str] = []
    for el in box.find_all(_BLOCKS):
        if any(a is not box and a.name in ("p", "li", "table") for a in el.parents):
            continue  # its text is already inside the ancestor
        if el.name == "table":
            blocks += _table(el)
        elif el.name == "p":
            blocks.append(_text(el))
        elif el.name == "li":
            t = _text(el)
            blocks.append("- " + t if t else "")
        else:
            t = _text(el)
            blocks.append("#" * int(el.name[1]) + " " + t if t else "")
    out = [b for i, b in enumerate(blocks) if b and (i == 0 or b != blocks[i - 1])]
    return title, "\n\n".join(out)
