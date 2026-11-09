import argparse


def main(argv=None):
    parser = argparse.ArgumentParser(prog="arengov")
    # each phase adds sub.add_parser(...) with set_defaults(func=...)
    sub = parser.add_subparsers(dest="cmd", required=True)  # noqa: F841 (unused until phase 01)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
