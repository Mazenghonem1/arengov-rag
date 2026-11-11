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

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
