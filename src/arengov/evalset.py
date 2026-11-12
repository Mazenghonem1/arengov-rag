import json
import random
import re
from collections import Counter
from pathlib import Path

from arengov import config
from arengov.index import load_index

TYPES = ("single", "multi_turn", "unanswerable_near", "unanswerable_oos", "mixed_script")
UNANSWERABLE = ("unanswerable_near", "unanswerable_oos")
LANGS = ("ar", "en")
ORIGINS = ("human", "llm_assisted", "feedback")
# D33: questions per language for each type
EXPECTED_PER_LANG = {
    "single": 18,
    "multi_turn": 5,
    "unanswerable_near": 3,
    "unanswerable_oos": 2,
    "mixed_script": 2,
}
SINGLE_PER_CATEGORY = 12
FIELDS = {
    "id": str,
    "lang": str,
    "type": str,
    "category": str,
    "turns": list,
    "gold_page_ids": list,
    "reference_answer": str,
    "key_facts": list,
    "answerable": bool,
    "origin": str,
    "notes": str,
}
AR_RE = re.compile(r"[؀-ۿ]")
LATIN_RE = re.compile(r"[A-Za-z]")


def sample_pages(n: int = 30, seed: int = 1) -> list[dict]:
    pages = {}  # page_id -> first EN chunk (one entry per page)
    for c in load_index().chunks:
        if c["lang"] == "en":
            pages.setdefault(c["page_id"], c)
    rng = random.Random(seed)
    out = []
    for cat in config.CATEGORIES:
        pool = sorted(p for p, c in pages.items() if c["category"] == cat)
        out += [pages[p] for p in rng.sample(pool, min(n // 3, len(pool)))]
    print("category | page_id | EN title | EN url | AR url")
    for c in out:
        print(
            f"{c['category']} | {c['page_id']} | {c['title']} | {c['url']} | {c['pair_url'] or '—'}"
        )
    return out


def _load(path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text("utf-8").splitlines() if line.strip()]


def validate(path, strict: bool = False) -> list[str]:
    errors, questions, seen = [], [], set()
    known = {c["page_id"] for c in load_index().chunks}
    for n, line in enumerate(Path(path).read_text("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            q = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"line {n}: not valid JSON ({e.msg})")
            continue
        if not isinstance(q, dict):
            errors.append(f"line {n}: not a JSON object")
            continue
        questions.append(q)
        qid = q.get("id", f"line {n}")

        def err(msg, qid=qid):
            errors.append(f"{qid}: {msg}")

        for f, t in FIELDS.items():
            if f not in q:
                err(f"missing field {f}")
            elif not isinstance(q[f], t):
                err(f"{f} must be {t.__name__}")
        if not isinstance(q.get("id"), str) or not re.fullmatch(r"q\d{3}", q["id"]):
            err("id must match q\\d{3}")
        elif q["id"] in seen:
            err("duplicate id")
        else:
            seen.add(q["id"])
        for f, allowed in (
            ("type", TYPES),
            ("lang", LANGS),
            ("category", config.CATEGORIES),
            ("origin", ORIGINS),
        ):
            if f in q and q[f] not in allowed:
                err(f"{f}={q[f]!r} not in {allowed}")
        if "split" in q and q["split"] not in ("dev", "test"):
            err(f"split={q['split']!r} not in dev/test")

        # the rest needs well-typed fields
        if not all(isinstance(q.get(f), t) for f, t in FIELDS.items()):
            continue
        typ, turns = q["type"], q["turns"]
        if q["answerable"] != (typ not in UNANSWERABLE):
            err("answerable must be false exactly for the unanswerable types")
        if not turns or not all(isinstance(t, str) and t.strip() for t in turns):
            err("turns must be non-empty strings")
        lo, hi = (2, 3) if typ == "multi_turn" else (1, 1)
        if not lo <= len(turns) <= hi:
            err(f"{typ} needs {lo}-{hi} turns, has {len(turns)}")
        if typ == "mixed_script":
            text = " ".join(map(str, turns))
            if not (AR_RE.search(text) and LATIN_RE.search(text)):
                err("mixed_script turns need both Arabic and Latin letters")
        if typ in UNANSWERABLE:
            if q["gold_page_ids"] or q["key_facts"] or q["reference_answer"]:
                err("unanswerable needs empty gold_page_ids, key_facts, reference_answer")
        else:
            if not 1 <= len(q["gold_page_ids"]) <= 3:
                err("needs 1-3 gold_page_ids")
            for p in q["gold_page_ids"]:
                if p not in known:
                    err(f"gold page_id not in index: {p}")
            if not 2 <= len(q["key_facts"]) <= 4:
                err("needs 2-4 key_facts")
            if not q["reference_answer"].strip():
                err("reference_answer is empty")

    if strict:
        errors += _strict(questions)
    return errors


def _strict(questions: list[dict]) -> list[str]:
    errors = []
    counts = Counter((q.get("type"), q.get("lang")) for q in questions)
    for typ, per_lang in EXPECTED_PER_LANG.items():
        for lang in LANGS:
            if counts[(typ, lang)] != per_lang:
                errors.append(f"{typ}/{lang}: expected {per_lang}, found {counts[(typ, lang)]}")
    cats = Counter(q.get("category") for q in questions if q.get("type") == "single")
    for cat in config.CATEGORIES:
        if cats[cat] != SINGLE_PER_CATEGORY:
            errors.append(f"single/{cat}: expected {SINGLE_PER_CATEGORY}, found {cats[cat]}")
    if any("split" not in q for q in questions):
        errors.append("some questions have no split; run assign-splits")
    splits = Counter(q.get("split") for q in questions)
    if splits["dev"] != 40 or splits["test"] != 20:
        errors.append(f"splits must be 40 dev / 20 test, found {splits['dev']}/{splits['test']}")
    return errors


def count_table(path) -> str:
    c = Counter((q.get("type"), q.get("lang"), q.get("split", "-")) for q in _load(path))
    lines = [f"{'type':<20} {'lang':<5} {'dev':>4} {'test':>5} {'unset':>6}"]
    for typ in TYPES:
        for lang in LANGS:
            lines.append(
                f"{typ:<20} {lang:<5} {c[(typ, lang, 'dev')]:>4} "
                f"{c[(typ, lang, 'test')]:>5} {c[(typ, lang, '-')]:>6}"
            )
    return "\n".join(lines)


def assign_splits(path, seed: int = 13) -> None:
    questions = _load(path)
    rng = random.Random(seed)
    groups: dict[tuple, list[dict]] = {}
    for q in sorted(questions, key=lambda q: (q["type"], q["lang"], q["id"])):
        groups.setdefault((q["type"], q["lang"]), []).append(q)
    ordered = []
    for key in sorted(groups):
        rng.shuffle(groups[key])
        ordered += groups[key]
    for i, q in enumerate(ordered):
        q["split"] = "test" if i % 3 == 2 else "dev"
    questions.sort(key=lambda q: q["id"])
    Path(path).write_text(
        "".join(json.dumps(q, ensure_ascii=False) + "\n" for q in questions), encoding="utf-8"
    )
