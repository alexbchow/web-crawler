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

from collections import deque


class Frontier:
    """Tracks which URLs to crawl next and which have already been seen."""

    def __init__(self) -> None:
        self.queue = deque()
        self.seen = set()

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
