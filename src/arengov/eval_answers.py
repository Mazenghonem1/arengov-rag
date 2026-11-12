import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path

from arengov import config, pipeline
from arengov.eval_retrieval import RESULTS_MD, _git_sha
from arengov.index import load_index
from arengov.judge import CRITERIA, judge
from arengov.text_ar import detect_lang

DET = ("refusal_correct", "lang_match", "citation_valid")
CHECKS = DET + CRITERIA
THRESHOLDS = config.EVAL_DIR / "thresholds.json"
GATED = {
    "retrieval": ("recall@5", "mrr@10"),
    "answers": ("refusal_correct", "lang_match", "faithfulness", "citation_accuracy"),
}
_MARKER = re.compile(r"\[\d+\]|https?://\S+")


def _questions(split):
    path = config.EVAL_DIR / "questions.jsonl"
    qs = [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]
    return [q for q in qs if split in ("all", q["split"])]


def det_checks(q, out):
    """Deterministic checks; None = not applicable to this question."""
    text = _MARKER.sub("", out["answer"])
    answered = not out["refused"]
    return {
        "refusal_correct": out["refused"] == (not q["answerable"]),
        "lang_match": detect_lang(text) == q["lang"],
        "citation_valid": (len(out["citations"]) >= 1 and not out["invalid_citations"])
        if answered
        else None,
    }


def _judge_row(row, q, chunks):
    res = judge(
        q["turns"][-1],
        chunks,
        row["answer"],
        q["reference_answer"],
        q["key_facts"],
        q["turns"][:-1],
    )
    row["judge"] = {k: res[k] for k in CRITERIA}
    row["judge_cost_usd"] = res["cost_usd"]
    row["checks"] |= {k: res[k]["pass"] for k in CRITERIA}


def _fail(row, q, err):
    print(f"ERROR {q['id']}: {err!r}", file=sys.stderr)
    row["error"] = repr(err)
    # an errored question fails every check that would have applied to it
    row["checks"] = {k: False for k in DET} | {
        k: (False if q["answerable"] else None) for k in CRITERIA
    }


def _row(q, out):
    row = {
        "id": q["id"],
        "lang": q["lang"],
        "type": q["type"],
        "answerable": q["answerable"],
        "answer": out["answer"],
        "citations": [{k: c[k] for k in ("n", "url", "title")} for c in out["citations"]],
        "refused": out["refused"],
        "final_chunk_ids": out["final_chunk_ids"],
        "latency_ms": out["latency_ms"],
        "cost_usd": out["usage"]["cost_usd"],
        "checks": det_checks(q, out) | {k: None for k in CRITERIA},
        "judge": None,
        "judge_cost_usd": 0.0,
        "error": None,
    }
    return row


def _rate(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def _pct(vals, p):
    vals = sorted(vals)
    return vals[min(len(vals) - 1, math.ceil(p * len(vals)) - 1)] if vals else None


def _rates(rows):
    return {k: _rate([r["checks"][k] for r in rows]) for k in CHECKS}


def _group(rows, key):
    out = {}
    for v in sorted({r[key] for r in rows}):
        sub = [r for r in rows if r[key] == v]
        out[v] = {"n": len(sub)} | _rates(sub)
    return out


def _summary(rows, *, label, split, index_version, backend, judge_model, timestamp):
    ok = [r for r in rows if not r["error"]]
    lat = [r["latency_ms"] for r in ok]
    gen_cost = sum(r["cost_usd"] for r in ok)
    return {
        "kind": "answers",
        "label": label,
        "split": split,
        "index_version": index_version,
        "git_sha": _git_sha(),
        "timestamp": timestamp,
        "backend": backend,
        "gen_model": config.GEN_MODEL if backend == "openai" else config.OLLAMA_MODEL,
        "judge_model": judge_model,
        "n": len(rows),
        "n_judged": sum(r["judge"] is not None for r in rows),
        "errors": len(rows) - len(ok),
        "metrics": _rates(rows)
        | {
            "latency_p50_ms": _pct(lat, 0.5),
            "latency_p95_ms": _pct(lat, 0.95),
            "cost_per_q_usd": gen_cost / len(ok) if ok else None,
        },
        "by_lang": _group(rows, "lang"),
        "by_type": _group(rows, "type"),
        "gen_cost_usd": gen_cost,
        "eval_cost_usd": sum(r["judge_cost_usd"] for r in rows),
    }


def _row_md(s, date):
    m = s["metrics"]
    pct = lambda v: "—" if v is None else f"{v:.0%}"  # noqa: E731
    cells = [date, s["label"], s["split"], s["index_version"]] + ["—"] * 7  # retrieval columns
    cells += [s["backend"], s["judge_model"]]
    cells += [pct(m[k]) for k in CHECKS]
    cells += [f"{m['latency_p95_ms']:.0f}", f"${m['cost_per_q_usd']:.5f}"]
    return "| " + " | ".join(cells) + " |\n"


def _print(s, rows):
    print(f"{s['label']} / {s['split']} n={s['n']} judged={s['n_judged']} errors={s['errors']}")
    print(f"backend={s['backend']} gen={s['gen_model']} judge={s['judge_model']}")
    print(f"{'':<14}{'n':>4}" + "".join(f"{k[:11]:>13}" for k in CHECKS))
    groups = [("overall", {"n": s["n"]} | s["metrics"])]
    groups += [(f"lang={k}", v) for k, v in s["by_lang"].items()]
    groups += [(f"type={k}", v) for k, v in s["by_type"].items()]
    for name, v in groups:
        print(f"{name:<14}{v['n']:>4}" + "".join(f"{_fmt(v[k]):>13}" for k in CHECKS))
    m = s["metrics"]
    if m["latency_p50_ms"] is not None:
        print(
            f"latency p50/p95 {m['latency_p50_ms']:.0f}/{m['latency_p95_ms']:.0f} ms, "
            f"gen ${s['gen_cost_usd']:.4f} ({m['cost_per_q_usd']:.5f}/q)"
        )
    print(f"eval_cost_usd (judge) ${s['eval_cost_usd']:.4f}")
    for k in CHECKS:
        failed = [r["id"] for r in rows if r["checks"][k] is False]
        if failed:
            print(f"failed {k}: {' '.join(failed)}")


def _fmt(v):
    return "—" if v is None else f"{v:.0%}"


def _write(s, rows, record, out):
    now = datetime.fromisoformat(s["timestamp"])
    stem = f"{now:%Y%m%d-%H%M}_answers_{s['label']}_{s['split']}"
    res = config.EVAL_DIR / "results"
    (res / "details").mkdir(parents=True, exist_ok=True)
    text = json.dumps(s, indent=2, ensure_ascii=False) + "\n"
    (res / f"{stem}.json").write_text(text, "utf-8")
    (res / "details" / f"{stem}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8"
    )
    if out:
        out.write_text(text, "utf-8")
    _print(s, rows)
    if record:
        with RESULTS_MD.open("a", encoding="utf-8") as f:
            f.write(_row_md(s, f"{now:%Y-%m-%d}"))


def run(split, *, backend="openai", judge_model=None, label, record=False, out=None):
    config.LLM_BACKEND = backend  # default is openai even if .env says ollama (D67)
    if judge_model:
        config.JUDGE_MODEL = judge_model
    qs = _questions(split)
    rows = []
    for q in qs:
        try:
            o = pipeline.answer([{"role": "user", "content": t} for t in q["turns"]], "auto")
            row = _row(q, o)
        except Exception as e:  # keep going: one bad call must not lose the whole run
            row = _row(
                q,
                {
                    "answer": "",
                    "citations": [],
                    "refused": False,
                    "invalid_citations": [],
                    "final_chunk_ids": [],
                    "latency_ms": 0,
                    "usage": {"cost_usd": 0},
                },
            )
            _fail(row, q, e)
            rows.append(row)
            continue
        if q["answerable"] and not o["refused"]:
            try:
                _judge_row(row, q, o["_chunks"])
            except Exception as e:
                _fail(row, q, e)
        rows.append(row)
    s = _summary(
        rows,
        label=label,
        split=split,
        index_version=config.INDEX_VERSION_FILE.read_text("utf-8").strip(),
        backend=backend,
        judge_model=config.JUDGE_MODEL,
        timestamp=datetime.now().isoformat(timespec="seconds"),
    )
    _write(s, rows, record, out)
    return s


def rejudge(details_path, judge_model=None, label=None, record=False, out=None):
    """Re-run only the judge on stored outputs; generation metrics and det. checks are kept."""
    if judge_model:
        config.JUDGE_MODEL = judge_model
    details_path = Path(details_path)
    old = json.loads(
        (details_path.parent.parent / (details_path.stem + ".json")).read_text("utf-8")
    )
    rows = [json.loads(line) for line in details_path.read_text("utf-8").splitlines() if line]
    qs = {q["id"]: q for q in _questions("all")}
    by_id = {c["chunk_id"]: c for c in load_index(old["index_version"]).chunks}
    for r in rows:
        q = qs[r["id"]]
        r["judge"], r["judge_cost_usd"] = None, 0.0
        if r["error"] or not q["answerable"] or r["refused"]:
            continue
        r["checks"] |= {k: None for k in CRITERIA}
        try:
            _judge_row(r, q, [by_id[c] for c in r["final_chunk_ids"]])
        except Exception as e:
            _fail(r, q, e)
    s = _summary(
        rows,
        label=label or f"{old['label']}-rejudge-{config.JUDGE_MODEL}",
        split=old["split"],
        index_version=old["index_version"],
        backend=old["backend"],
        judge_model=config.JUDGE_MODEL,
        timestamp=datetime.now().isoformat(timespec="seconds"),
    )
    _write(s, rows, record, out)
    return s


# ---- thresholds (D37) ----


def threshold_for(baseline):
    # 5 points of margin, rounded down to a multiple of 5; round() guards float noise
    return max(0.0, math.floor((round(baseline * 100, 6) - 5) / 5) * 5 / 100)


def _load(path):
    return json.loads(Path(path).read_text("utf-8"))


def set_thresholds(retrieval_path, answers_path):
    old = _load(THRESHOLDS) if THRESHOLDS.exists() else {}
    new = {"split": "test", "retrieval": {}, "answers": {}}
    for kind, path in (("retrieval", retrieval_path), ("answers", answers_path)):
        s = _load(path)
        if s["split"] != "test" or s["kind"] != kind:
            raise ValueError(f"{path}: need a test-split {kind} summary")
        for m in GATED[kind]:
            if s["metrics"].get(m) is None:
                continue
            prev = old.get(kind, {}).get(m)
            val = threshold_for(s["metrics"][m])
            new[kind][m] = val if prev is None else max(prev, val)  # ratchet: never lower
            print(f"{kind}.{m}: {prev} -> {new[kind][m]} (baseline {s['metrics'][m]:.3f})")
    THRESHOLDS.write_text(json.dumps(new, indent=2) + "\n", "utf-8")
    return new


def check_thresholds(paths):
    th = _load(THRESHOLDS)
    ok = True
    print(f"{'summary':<56}{'metric':<18}{'value':>8}{'min':>8}  result")
    for p in paths:
        s = _load(p)
        for m, t in th.get(s["kind"], {}).items():
            v = s["metrics"].get(m)
            if v is None:
                continue
            good = v >= t - 1e-9
            ok &= good
            print(f"{Path(p).name:<56}{m:<18}{v:>8.3f}{t:>8.2f}  {'pass' if good else 'FAIL'}")
    return ok
