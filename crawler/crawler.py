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

from crawler.fetcher import fetch
from crawler.frontier import Frontier
from crawler.parser import extract_links


class Crawler:
    """Single-threaded, synchronous web crawler."""

    def __init__(self, seed_url: str, max_pages: int = 50) -> None:
        """
        Args:
            seed_url: The starting URL for the crawl.
            max_pages: Stop after crawling this many pages.
        """
        raise NotImplementedError("Implement this last.")

    def run(self) -> None:
        """Start the crawl loop and run until completion."""
        raise NotImplementedError
