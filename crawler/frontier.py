"""
URL frontier — deduplication and ordering for the crawl.

Backed by SQLite for crash-safe persistence. URLs flow from the queue
table (pending) to the seen table (completed) as they are fetched.
The resume flag reloads both tables into memory on startup.
"""

import logging
import sqlite3
import time
import threading
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from queue import Queue, Empty

logger = logging.getLogger(__name__)


class Frontier:
    """Tracks which URLs to crawl next and which have already been seen."""

    def __init__(self, db_path: str = "frontier.db", resume: bool = False) -> None:
        self.queue = Queue()
        self.seen = set()
        self.last_fetched = {}
        self.robots_cache = {}
        self._lock = threading.Lock()

        self.con = sqlite3.connect(db_path)
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("CREATE TABLE IF NOT EXISTS seen (url TEXT PRIMARY KEY)")
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS queue (url TEXT, added_at TIMESTAMP)"
        )
        self.con.commit()

        if resume:
            for row in self.con.execute("SELECT url FROM seen"):
                self.seen.add(row[0])
            for row in self.con.execute("SELECT url FROM queue"):
                self.seen.add(row[0])
                self.queue.put(row[0])
        else:
            self.con.execute("DELETE FROM seen")
            self.con.execute("DELETE FROM queue")
            self.con.commit()

    def add(self, url: str) -> None:
        """Add a URL to the frontier if it hasn't been seen before.

        Args:
            url: An absolute URL to enqueue.
        """
        with self._lock:
            if url not in self.seen:
                self.seen.add(url)
                self.queue.put(url)
                self.con.execute(
                    "INSERT OR IGNORE INTO queue (url, added_at) VALUES (?, datetime('now'))",
                    (url,),
                )
                self.con.commit()

    def next(self, block:bool = False) -> str | None:
        """Return the next URL to crawl, or None if the frontier is empty."""
        try:
            return self.queue.get(block=block, timeout=1.0)
        except Empty:
            return None

    def is_empty(self) -> bool:
        """Return True if there are no URLs left to crawl."""
        return self.queue.empty()

    def is_allowed(self, url: str, user_agent: str) -> bool:
        """Return True if robots.txt permits fetching this URL."""
        parsed = urlparse(url)
        domain, scheme = parsed.netloc, parsed.scheme
        if domain not in self.robots_cache:
            rp = RobotFileParser()
            rp.set_url(f"{scheme}://{domain}/robots.txt")
            try:
                rp.read()
            except Exception as e:
                logger.warning("Failed to fetch robots.txt for %s: %s", domain, e)
            self.robots_cache[domain] = rp
        return self.robots_cache[domain].can_fetch(user_agent, url)

    def seconds_until_allowed(
        self, url: str, user_agent: str, crawl_delay: float = 1.0
    ) -> float:
        """Return how many seconds to wait before fetching this URL.

        Args:
            url: The URL about to be fetched.
            user_agent: The crawler's User-Agent string.
            crawl_delay: Fallback minimum seconds between requests to the same domain.

        Returns:
            Seconds to wait; 0.0 means fetch immediately.
        """
        domain = urlparse(url).netloc
        rp = self.robots_cache.get(domain)
        if rp is not None:
            robots_delay = rp.crawl_delay(user_agent)
            if robots_delay is not None:
                crawl_delay = robots_delay
        if domain not in self.last_fetched:
            return 0.0
        elapsed = time.time() - self.last_fetched[domain]
        return max(0.0, crawl_delay - elapsed)

    def record_fetch(self, url: str) -> None:
        """Record that a URL was just fetched.

        Updates the per-domain crawl delay timestamp and moves the URL
        from the queue table to the seen table in SQLite.

        Args:
            url: The URL that was just fetched.
        """
        with self._lock:
            domain = urlparse(url).netloc
            self.last_fetched[domain] = time.time()
            self.con.execute("INSERT OR IGNORE INTO seen (url) VALUES (?)", (url,))
            self.con.execute("DELETE FROM queue WHERE url = ?", (url,))
            self.con.commit()
