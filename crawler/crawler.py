"""
Top-level crawl orchestration.

Wires together the fetcher, parser, frontier, and storage into a single-
threaded synchronous crawl loop. Handles per-domain politeness, robots.txt
compliance, graceful SIGINT shutdown, and optional S3 storage.
"""

import logging
import signal
import time

import boto3
import threading
from requests import Session
from requests.exceptions import ConnectionError, HTTPError, Timeout, TooManyRedirects
from urllib.parse import urlparse

from crawler.fetcher import NonHTMLResponseError, fetch
from crawler.frontier import Frontier
from crawler.parser import extract_links, is_nofollow_page
from crawler.storage import store_page

logger = logging.getLogger(__name__)


class Crawler:
    """Single-threaded, synchronous web crawler."""

    def __init__(
        self,
        seed_url: str,
        max_pages: int = 50,
        domain: str = None,
        resume: bool = False,
        s3_bucket: str = None,
    ) -> None:
        """
        Args:
            seed_url: The starting URL for the crawl.
            max_pages: Stop after crawling this many pages.
            domain: If set, restricts crawl to this domain only.
            resume: If True, reload state from an existing frontier.db.
            s3_bucket: S3 bucket name to store crawled pages. If None, storage is skipped.
        """
        self.seed_url = seed_url
        self.max_pages = max_pages
        self.domain = domain
        self.s3_bucket = s3_bucket
        self._shutdown = False

        self.frontier = Frontier(resume=resume)
        self._local = threading.local()
        self.s3_client = boto3.client("s3") if s3_bucket else None

    def _get_session(self) -> Session:
        if not hasattr(self._local, "session"):
            s = Session()
            s.headers.update({"User-Agent": "MyCrawler/1.0 (+https://github.com/alexbchow/web-crawler)"})
            self._local.session = s                                                                                                                                                      
        return self._local.session

    def run(self) -> None:
        """Start the crawl loop and run until completion."""

        def _handle_sigint(_sig, _frame):
            logger.info("Shutting down gracefully...")
            self._shutdown = True

        signal.signal(signal.SIGINT, _handle_sigint)
        self.frontier.add(self.seed_url)
        pages_crawled = 0
        while (
            not self.frontier.is_empty()
            and pages_crawled != self.max_pages
            and not self._shutdown
        ):
            url = self.frontier.next()
            domain = urlparse(url).netloc
            pages_crawled += 1

            if self.domain and self.domain != domain:
                continue
            if not self.frontier.is_allowed(url, self._get_session().headers["User-Agent"]):
                logger.debug("Skipping (robots.txt): %s", url)
                continue

            wait_time = self.frontier.seconds_until_allowed(
                url, self._get_session().headers["User-Agent"]
            )
            if wait_time > 0:
                logger.debug("Waiting %.2fs for %s", wait_time, url)
                time.sleep(wait_time)

            try:
                html, final_url = fetch(url, self._get_session())
                self.frontier.seen.add(final_url)
                if is_nofollow_page(html):
                    logger.debug("Skipping links (nofollow page): %s", url)
                    continue
            except NonHTMLResponseError as e:
                logger.debug("Skipped %s: %s", url, e)
                continue
            except (Timeout, ConnectionError) as e:
                logger.warning("Network error %s: %s", url, e)
                continue
            except TooManyRedirects as e:
                logger.warning("Too many redirects %s: %s", url, e)
                continue
            except HTTPError as e:
                logger.warning("HTTP error %s: %s", url, e)
                continue
            except Exception as e:
                logger.error("Unexpected error %s: %s", url, e)
                continue
            finally:
                self.frontier.record_fetch(url)

            if self.s3_bucket:
                try:
                    key = store_page(url, html, self.s3_bucket, self.s3_client)
                    logger.debug("Stored %s → s3://%s/%s", url, self.s3_bucket, key)
                except Exception as e:
                    logger.warning("S3 upload failed for %s: %s", url, e)

            links = extract_links(html, url)
            logger.info(
                "page_crawled",
                extra={
                    "url": url,
                    "links_found": len(links),
                    "stored": bool(self.s3_bucket),
                },
            )
            for link in links:
                self.frontier.add(link)
