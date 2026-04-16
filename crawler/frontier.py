"""
URL frontier — the scheduler of the crawler.

The frontier has two jobs:
  1. Deduplication: never return a URL that has already been crawled.
  2. Ordering: decide which URL to crawl next (and when).

Implement this after fetcher.py is working. Start simple: a set for seen
URLs and a queue.Queue for pending ones. Get it working before optimizing.

Questions to answer before you implement:
  - What makes two URLs "the same"? Is http://example.com/path and
    http://example.com/path/ the same URL? What about ?utm_source=twitter?
  - What happens when the queue is empty but there are pending retries?
  - How will you enforce per-domain crawl delays in Phase 2?
"""

import logging
import time
from collections import deque
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)


class Frontier:
    """Tracks which URLs to crawl next and which have already been seen."""

    def __init__(self) -> None:
        self.queue = deque()
        self.seen = set()
        self.last_fetched = {}
        self.robots_cache = {}

    def add(self, url: str) -> None:
        """Add a URL to the frontier if it hasn't been seen before.

        Args:
            url: An absolute URL to enqueue.
        """
        if url not in self.seen:
            self.seen.add(url)
            self.queue.append(url)

    def next(self) -> str | None:
        """Return the next URL to crawl, or None if the frontier is empty.

        Returns:
            An absolute URL, or None if there is nothing left to crawl.
        """
        return self.queue.popleft() if not self.is_empty() else None

    def is_empty(self) -> bool:
        """Return True if there are no URLs left to crawl."""
        return not self.queue

    def is_allowed(self, url: str, user_agent: str) -> bool:
        parsed = urlparse(url)
        domain, scheme = parsed.netloc, parsed.scheme
        if domain not in self.robots_cache:
            rp = RobotFileParser()
            rp.set_url(
                f"{scheme}://{domain}/robots.txt"
            )  # https://www.youtube.com -> https://www.youtube.com/robots.txt
            try:
                rp.read()
            except Exception as e:
                logger.warning("Failed to fetch robots.txt for %s: %s", domain, e)
            self.robots_cache[domain] = rp
        return self.robots_cache[domain].can_fetch(user_agent, url)

    def seconds_until_allowed(self, url: str, crawl_delay: float = 1.0) -> float:
        """Return how many seconds to wait before fetching this URL.

        Looks up the domain in last_fetched and computes how much of the
        crawl_delay period has already elapsed. Returns 0.0 if enough time
        has passed or if the domain has never been fetched.

        Args:
            url: The URL about to be fetched.
            crawl_delay: Minimum seconds between requests to the same domain.

        Returns:
            Seconds to wait (0.0 means fetch immediately).

        Implementation:
            1. Extract domain with urlparse(url).netloc
            2. If domain not in self.last_fetched, return 0.0
            3. elapsed = time.time() - self.last_fetched[domain]
            4. return max(0.0, crawl_delay - elapsed)
        """
        domain = urlparse(url).netloc
        if domain not in self.last_fetched:
            return 0.0
        elapsed = time.time() - self.last_fetched[domain]
        return max(0.0, crawl_delay - elapsed)

    def record_fetch(self, url: str) -> None:
        """Record that a URL's domain was just fetched.

        Call this immediately after a successful or failed fetch so the
        next request to the same domain respects the crawl delay.

        Args:
            url: The URL that was just fetched.

        Implementation:
            1. Extract domain with urlparse(url).netloc
            2. self.last_fetched[domain] = time.time()
        """
        domain = urlparse(url).netloc
        self.last_fetched[domain] = time.time()
