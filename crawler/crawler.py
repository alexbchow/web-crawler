"""
Top-level crawl orchestration.

Wire together the fetcher, parser, and frontier here.
Implement this last, after the other three modules are working.

The crawl loop is simple in concept:
  1. Pull a URL from the frontier.
  2. Fetch it.
  3. Parse links from the response.
  4. Add discovered links back to the frontier.
  5. Repeat.

The interesting engineering is in what happens around that loop:
  - How do you handle fetch errors without stopping the whole crawl?
  - How do you enforce a maximum page limit?
  - Where do you store results? (Print to stdout for now is fine.)
  - How will you know when the crawl is "done"?
"""

import logging
import time

from crawler.fetcher import fetch
from crawler.frontier import Frontier
from crawler.parser import extract_links
from requests import Session

logger = logging.getLogger(__name__)


class Crawler:
    """Single-threaded, synchronous web crawler."""

    def __init__(self, seed_url: str, max_pages: int = 50) -> None:
        """
        Args:
            seed_url: The starting URL for the crawl.
            max_pages: Stop after crawling this many pages.
        """
        self.max_pages = max_pages
        self.seed_url = seed_url
        self.frontier = Frontier()
        self.session = Session()
        self.session.headers.update(
            {"User-Agent": "MyCrawler/1.0 (+https://github.com/alexbchow/web-crawler)"}
        )

    def run(self) -> None:
        """Start the crawl loop and run until completion."""
        self.frontier.add(self.seed_url)
        pages_crawled = 0
        while not self.frontier.is_empty() and pages_crawled != self.max_pages:
            url = self.frontier.next()
            logger.info("[%d/%d] Crawling: %s", pages_crawled, self.max_pages, url)
            pages_crawled += 1
            if not self.frontier.is_allowed(url, self.session.headers["User-Agent"]):
                logger.debug("Skipping (robots.txt): %s", url)
                continue
            wait_time = self.frontier.seconds_until_allowed(url)
            if wait_time > 0:
                logger.debug("Waiting %.2fs for %s", wait_time, url)
                time.sleep(wait_time)
            try:
                html = fetch(url, self.session)
            except Exception as e:
                logger.warning("Failed %s: %s", url, e)
                continue
            finally:
                self.frontier.record_fetch(url)
            links = extract_links(html, url)
            logger.info("  Found %d links", len(links))
            for link in links:
                self.frontier.add(link)
