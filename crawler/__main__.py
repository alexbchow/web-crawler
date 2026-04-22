"""
CLI entry point for the crawler.

Usage:
    python -m crawler <seed_url> [--max-pages N] [--domain DOMAIN]
                                 [--resume] [--s3-bucket BUCKET]
"""

import argparse
import logging
import yaml
import json

from crawler.crawler import Crawler


class JSONFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "time": self.formatTime(record),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        for key in ("url", "links_found", "stored"):
            if hasattr(record, key):
                data[key] = getattr(record, key)
        return json.dumps(data)


def main() -> None:
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config", type=str, default="config.yaml")
    pre_args, _ = pre_parser.parse_known_args()

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)

    with open(pre_args.config) as f:
        config = yaml.safe_load(f)

    parser = argparse.ArgumentParser(description="Single-threaded web crawler.")
    parser.add_argument("--config", type=str, default="config.yaml")

    parser.add_argument(
        "seed_url",
        type=str,
        nargs="?",
        default=config.get("seed_url"),
        help="URL to start crawling from",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=config.get("max_pages", 50),
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
