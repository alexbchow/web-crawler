"""
Entry point for running the crawler as a module:
    python -m crawler <seed_url> [--max-pages N]

argparse docs: https://docs.python.org/3/library/argparse.html

Steps to implement:
  1. Create an ArgumentParser with a description of the tool.
  2. Add a positional argument for seed_url.
  3. Add an optional --max-pages argument (type=int, with a sensible default).
  4. Parse the args and pass them to Crawler.
"""

import argparse
from crawler.crawler import Crawler


def main() -> None:
    parser = argparse.ArgumentParser(description="Basic web crawler.")

    # TODO: add positional argument: seed_url (type str)
    parser.add_argument("seed_url", type=str, help="seed url for crawler to start with")
    # TODO: add optional argument: --max-pages (type int, default your choice)
    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="max pages crawler will navigate before stopping",
    )
    args = parser.parse_args()
    Crawler(args.seed_url, max_pages=args.max_pages).run()


if __name__ == "__main__":
    main()
