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
import logging

from crawler.crawler import Crawler


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    parser = argparse.ArgumentParser(description="Basic web crawler.")

    parser.add_argument("seed_url", type=str, help="seed url for crawler to start with")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="max pages crawler will navigate before stopping",
    )
    parser.add_argument("--domain", type=str, help="scope control")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="resume crawl from existing frontier.db instead of starting fresh",
    )
    args = parser.parse_args()
    Crawler(
        args.seed_url, max_pages=args.max_pages, domain=args.domain, resume=args.resume
    ).run()


if __name__ == "__main__":
    main()
