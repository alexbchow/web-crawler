from requests import Session
"""
HTTP fetching.

Implement this after parser.py is working and tested. Start synchronous
(requests library) — you can always swap the transport layer for async later.

Key concepts you'll need:
  - requests.Session: reuses TCP connections (connection pooling)
  - Timeouts: requests.get(url, timeout=(connect_timeout, read_timeout))
    These are different things. Understand both before setting them.
  - User-Agent: servers block crawlers with no UA or with "python-requests".
    Use a descriptive UA string that identifies your bot.
  - Status codes: 200 is not the only success case. What about 201? What
    about 404 — should you return empty or raise? Decide and document it.
  - robots.txt: before implementing fetch, read RFC 9309 (it's short).
"""


def fetch(url: str, session: Session = None) -> str:
    """Fetch a URL and return its HTML content.

    Args:
        url: The URL to fetch.

    Returns:
        The decoded HTML body of the response.

    Raises:
        Decide what exceptions this should surface vs. swallow.
        Document your decision here before you implement it.
    """
    session.headers.update({
      "User-Agent": "MyCrawler/1.0 (+https://github.com/alexbchow/web-crawler)"
})
    response = session.get(url, timeout = (3, 30))
    response.raise_for_status()
    return response.text

