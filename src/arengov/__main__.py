import argparse
import sys
from datetime import date

from arengov import config, crawl
from arengov.index import build_index, load_index


def _crawl(args):
    crawl.crawl(args.snapshot_id or date.today().isoformat())


def _diff(args):
    d = crawl.diff(config.SNAPSHOT_ROOT / args.old, config.SNAPSHOT_ROOT / args.new)
    print(f"new: {len(d['new'])}, changed: {len(d['changed'])}, removed: {len(d['removed'])}")
    for kind, urls in d.items():
        for url in urls:
            print(f"{kind}\t{url}")


def _build_index(args):
    build_index(args.snapshot, args.version)
    config.INDEX_VERSION_FILE.write_text(args.version + "\n", encoding="utf-8")


def _search(args):
    from arengov.pipeline import retrieve

    r = retrieve(args.query, lang_filter=args.lang_filter, use_norm=not args.no_norm)
    chunks = load_index().chunks
    for rank, (i, score) in enumerate(r["ranked"][: args.k], 1):
        print(f"{rank:>2}  {score:7.3f}  {chunks[i]['chunk_id']}  {chunks[i]['heading_path']}")


def _ask(args):
    from arengov.pipeline import answer

    if args.backend:
        config.LLM_BACKEND = args.backend
    r = answer([{"role": "user", "content": args.question}], args.lang)
    print(r["answer"])
    for c in r["citations"]:
        print(f"[{c['n']}] {c['title']} - {c['url']}")
    u = r["usage"]
    print(f"\nrefused={r['refused']} reason={r['refusal_reason']} lang={r['lang']}")
    print(
        f"tokens in/out={u['input_tokens']}/{u['output_tokens']} "
        f"cost=${u['cost_usd']:.5f} latency={r['latency_ms']:.0f}ms"
    )


def _sample_pages(args):
    from arengov.evalset import sample_pages

    sample_pages(args.n, args.seed)


def _validate_eval(args):
    from arengov.evalset import count_table, validate

    path = config.EVAL_DIR / "questions.jsonl"
    errors = validate(path, strict=args.strict)
    print(count_table(path))
    for e in errors:
        print(e)
    if errors:
        print(f"{len(errors)} error(s)")
        sys.exit(1)
    print("ok")


def _assign_splits(args):
    from arengov.evalset import assign_splits

    assign_splits(config.EVAL_DIR / "questions.jsonl", args.seed)


def _eval_retrieval(args):
    from pathlib import Path

    from arengov.eval_retrieval import run

    run(
        args.split,
        mode=args.mode,
        use_rerank=not args.no_rerank,
        use_norm=not args.no_norm,
        cross_lingual=args.cross_lingual,
        label=args.label,
        record=args.record,
        out=Path(args.out) if args.out else None,
    )


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, breaking Arabic
    parser = argparse.ArgumentParser(prog="arengov")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("crawl", help="crawl u.ae into data/snapshots/<id>/")
    p.add_argument("--snapshot-id", help="YYYY-MM-DD (default: today); reuse to resume")
    p.set_defaults(func=_crawl)

    p = sub.add_parser("diff", help="compare two snapshots")
    p.add_argument("old")
    p.add_argument("new")
    p.set_defaults(func=_diff)

    p = sub.add_parser("build-index", help="clean + chunk a snapshot into data/index/<version>/")
    p.add_argument("--snapshot", required=True)
    p.add_argument("--version", required=True)
    p.set_defaults(func=_build_index)

    p = sub.add_parser("search", help="BM25 search over the index")
    p.add_argument("query")
    p.add_argument("--lang-filter", choices=["ar", "en"])
    p.add_argument("--no-norm", action="store_true", help="skip normalization/stemming")
    p.add_argument("-k", type=int, default=10)
    p.set_defaults(func=_search)

    p = sub.add_parser("ask", help="answer a question with citations")
    p.add_argument("question")
    p.add_argument("--lang", choices=["auto", "ar", "en"], default="auto")
    p.add_argument("--backend", choices=["openai", "ollama"])
    p.set_defaults(func=_ask)

    p = sub.add_parser("sample-pages", help="random EN pages per category to write questions from")
    p.add_argument("--n", type=int, default=30)
    p.add_argument("--seed", type=int, default=1)
    p.set_defaults(func=_sample_pages)

    p = sub.add_parser("validate-eval", help="check eval/questions.jsonl")
    p.add_argument("--strict", action="store_true", help="also check counts and splits")
    p.set_defaults(func=_validate_eval)

    p = sub.add_parser("assign-splits", help="seeded dev/test split of eval/questions.jsonl")
    p.add_argument("--seed", type=int, default=13)
    p.set_defaults(func=_assign_splits)

    p = sub.add_parser("eval-retrieval", help="recall@k / MRR on the eval set")
    p.add_argument("--split", choices=["dev", "test", "all"], required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--mode", default="bm25")
    p.add_argument("--cross-lingual", action="store_true")
    p.add_argument("--no-norm", action="store_true")
    p.add_argument("--no-rerank", action="store_true")
    p.add_argument("--record", action="store_true", help="append a row to docs/results.md")
    p.add_argument("--out", help="also write the summary JSON here")
    p.set_defaults(func=_eval_retrieval)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
