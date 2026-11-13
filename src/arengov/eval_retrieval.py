import json
import subprocess
from collections import defaultdict
from datetime import datetime

from arengov import config, pipeline
from arengov.index import load_index
from arengov.rewrite import rewrite

ANSWERABLE = ("single", "multi_turn", "mixed_script")
RESULTS_MD = config.ROOT / "docs" / "results.md"
METRICS = ("recall@5", "recall@20", "mrr@10")


def hit_at(page_ids, gold, k):
    return any(p in gold for p in page_ids[:k])


def rr_at(page_ids, gold, k):
    for rank, p in enumerate(page_ids[:k], 1):
        if p in gold:
            return 1 / rank
    return 0.0


def _mean(rows):
    return {m: sum(r[m] for r in rows) / len(rows) for m in METRICS} | {"n": len(rows)}


def _group(rows, key):
    groups = defaultdict(list)
    for r in rows:
        groups[r[key]].append(r)
    return {k: _mean(v) for k, v in sorted(groups.items())}


def _git_sha():
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=config.ROOT
        )
        return out.stdout.strip() or None
    except OSError:
        return None


def _row_md(s, date):
    c, m = s["config"], s["metrics"]
    cells = [
        date,
        s["label"],
        s["split"],
        s["index_version"],
        c["mode"],
        "yes" if c["cross_lingual"] else "no",
        "yes" if c["use_rerank"] else "no",
        "yes" if c["use_norm"] else "no",
        f"{m['recall@5']:.0%}",
        f"{m['recall@20']:.0%}",
        f"{m['mrr@10']:.2f}",
    ] + ["—"] * 10  # answer columns, filled by phase 07
    return "| " + " | ".join(cells) + " |\n"


def _print_table(s):
    print(f"{s['label']} / {s['split']} (n={s['n']}) config={s['config']}")
    print(f"{'':<20}{'n':>4}  recall@5  recall@20  mrr@10")
    groups = [("overall", {**s["metrics"], "n": s["n"]})]
    groups += [(f"lang={k}", v) for k, v in s["by_lang"].items()]
    groups += [(f"type={k}", v) for k, v in s["by_type"].items()]
    for name, v in groups:
        r5, r20, mrr = v["recall@5"], v["recall@20"], v["mrr@10"]
        print(f"{name:<20}{v['n']:>4}  {r5:8.0%}  {r20:9.0%}  {mrr:6.2f}")


def _query(q):
    if q["type"] == "multi_turn":
        return rewrite(q["turns"][:-1][-config.HISTORY_MAX_TURNS :], q["turns"][-1], q["lang"])[0]
    return q["turns"][-1]


def run(
    split,
    *,
    mode="bm25",
    use_rerank=True,
    use_norm=True,
    cross_lingual=False,
    label,
    record=False,
    out=None,
    backend="openai",
):
    config.LLM_BACKEND = backend  # whole run, so a local env never leaks into metrics
    qs = [
        json.loads(line)
        for line in (config.EVAL_DIR / "questions.jsonl").read_text("utf-8").splitlines()
        if line.strip()
    ]
    qs = [q for q in qs if q["type"] in ANSWERABLE and split in ("all", q["split"])]
    chunks = load_index().chunks
    rows, details = [], []
    for q in qs:
        query = _query(q)
        lf = None
        if cross_lingual:
            lf = "en" if q["lang"] == "ar" else "ar"
        r = pipeline.retrieve(
            query, lang_filter=lf, mode=mode, use_rerank=use_rerank, use_norm=use_norm
        )
        pid = lambda ranked: [chunks[i]["page_id"] for i, _ in ranked]  # noqa: E731
        gold = q["gold_page_ids"]
        row = {
            "recall@5": float(hit_at(pid(r["final"]), gold, 5)),
            "recall@20": float(hit_at(pid(r["candidates"]), gold, 20)),
            "mrr@10": rr_at(pid(r["ranked"]), gold, 10),
            "lang": q["lang"],
            "type": q["type"],
        }
        rows.append(row)
        details.append(
            {
                "id": q["id"],
                "lang": q["lang"],
                "type": q["type"],
                "query": query,
                "gold": gold,
                "top5": pid(r["final"]),
                **{k: row[k] for k in METRICS},
            }
        )

    now = datetime.now()
    s = {
        "kind": "retrieval",
        "label": label,
        "split": split,
        "index_version": config.INDEX_VERSION_FILE.read_text("utf-8").strip(),
        "git_sha": _git_sha(),
        "timestamp": now.isoformat(timespec="seconds"),
        "config": {
            "mode": mode,
            "use_rerank": use_rerank,
            "use_norm": use_norm,
            "cross_lingual": cross_lingual,
        },
        "n": len(rows),
        "metrics": {m: v for m, v in _mean(rows).items() if m != "n"},
        "by_lang": _group(rows, "lang"),
        "by_type": _group(rows, "type"),
    }
    stem = f"{now:%Y%m%d-%H%M}_retrieval_{label}_{split}"
    res = config.EVAL_DIR / "results"
    (res / "details").mkdir(parents=True, exist_ok=True)
    text = json.dumps(s, indent=2, ensure_ascii=False) + "\n"
    (res / f"{stem}.json").write_text(text, "utf-8")
    (res / "details" / f"{stem}.jsonl").write_text(
        "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in details), "utf-8"
    )
    if out:
        out.write_text(text, "utf-8")
    _print_table(s)
    if record:
        with RESULTS_MD.open("a", encoding="utf-8") as f:
            f.write(_row_md(s, f"{now:%Y-%m-%d}"))
    return s


def choose_tau(rows):
    """rows: [(top_score, should_refuse)]. Max-F1 tau (ties: smallest); None if unsafe."""
    n_ans = sum(1 for _, r in rows if not r)
    best = None
    for tau in sorted({s for s, _ in rows}) + [float("inf")]:
        tp = sum(1 for s, r in rows if s < tau and r)
        fp = sum(1 for s, r in rows if s < tau and not r)
        fn = sum(1 for s, r in rows if s >= tau and r)
        p = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * p * rec / (p + rec) if p + rec else 0.0
        if best is None or f1 > best["f1"]:  # strict > keeps the smallest tau on ties
            best = {"tau": tau, "precision": p, "recall": rec, "f1": f1, "refused_answerable": fp}
    best["n_answerable"] = n_ans
    best["safe"] = best["f1"] >= 0.5 and best["refused_answerable"] <= 0.1 * n_ans
    return best


def pick_tau(split="dev", backend="openai"):
    config.LLM_BACKEND = backend
    qs = [
        json.loads(line)
        for line in (config.EVAL_DIR / "questions.jsonl").read_text("utf-8").splitlines()
        if line.strip()
    ]
    qs = [q for q in qs if q["split"] == split]
    rows = []
    for q in qs:
        r = pipeline.retrieve(_query(q), mode="hybrid", use_rerank=True)
        rows.append((r["top_score"], not q["answerable"], q["id"]))
    for s, refuse, qid in sorted(rows):
        print(f"{s:.4f}  {'REFUSE' if refuse else 'answer'}  {qid}")
    best = choose_tau([(s, r) for s, r, _ in rows])
    print(
        f"best tau={best['tau']:.4f} P={best['precision']:.2f} R={best['recall']:.2f} "
        f"F1={best['f1']:.2f}; refuses {best['refused_answerable']}/{best['n_answerable']} ans."
    )
    if best["safe"]:
        print(f"recommended GATE_TAU = {best['tau']:.3f}")
    else:
        print("recommended GATE_TAU = None (F1 < 0.5 or refuses > 10% of answerable)")
    return best
