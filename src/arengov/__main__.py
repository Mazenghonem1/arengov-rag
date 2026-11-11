import argparse
from datetime import date

from arengov import config, crawl


def _crawl(args):
    crawl.crawl(args.snapshot_id or date.today().isoformat())


def _diff(args):
    d = crawl.diff(config.SNAPSHOT_ROOT / args.old, config.SNAPSHOT_ROOT / args.new)
    print(f"new: {len(d['new'])}, changed: {len(d['changed'])}, removed: {len(d['removed'])}")
    for kind, urls in d.items():
        for url in urls:
            print(f"{kind}\t{url}")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="arengov")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("crawl", help="crawl u.ae into data/snapshots/<id>/")
    p.add_argument("--snapshot-id", help="YYYY-MM-DD (default: today); reuse to resume")
    p.set_defaults(func=_crawl)

    p = sub.add_parser("diff", help="compare two snapshots")
    p.add_argument("old")
    p.add_argument("new")
    p.set_defaults(func=_diff)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
