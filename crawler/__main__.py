"""
CLI entry point for the crawler.

Usage:
    python -m crawler <seed_url> [--max-pages N] [--domain DOMAIN]
                                 [--resume] [--s3-bucket BUCKET]
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
    parser = argparse.ArgumentParser(description="Single-threaded web crawler.")
    parser.add_argument("seed_url", type=str, help="URL to start crawling from")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="maximum number of pages to crawl (default: 50)",
    )
    parser.add_argument(
        "--domain",
        type=str,
        help="restrict crawl to this domain only",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="resume from an existing frontier.db instead of starting fresh",
    )
    parser.add_argument(
        "--s3-bucket",
        type=str,
        help="S3 bucket to store crawled pages (optional)",
    )
    args = parser.parse_args()
    Crawler(
        args.seed_url,
        max_pages=args.max_pages,
        domain=args.domain,
        resume=args.resume,
        s3_bucket=args.s3_bucket,
    ).run()


if __name__ == "__main__":
    main()
