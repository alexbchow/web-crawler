from requests import Session
from email.message import Message
import re

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


class NonHTMLResponseError(Exception):
    """Raised when a response Content-Type is not text/html."""


def fetch(url: str, session: Session) -> str:
    """Fetch a URL and return its HTML content.

    Args:
        url: The URL to fetch.

    Returns:
        The decoded HTML body of the response.

    Raises:
      requests.exceptions.HTTPError: on 4xx/5xx responses
      requests.exceptions.Timeout: if connect or read exceeds timeout
      requests.exceptions.ConnectionError: on DNS failure or refused connection
      requests.exceptiosn.TooManyRedirects: too many redirects
    """

    response = session.get(url, timeout=(3, 30))
    response.raise_for_status()
    content_type = response.headers.get("Content-Type")
    if "text/html" not in content_type:
        raise NonHTMLResponseError(f"{url} returned Content-Type: {content_type!r}")

    # TODO: Encoding detection (replace `return response.text` when done)
    # Step 1: Try to extract charset from the Content-Type header.
    #         Use email.message.Message to parse it cleanly:
    #           from email.message import Message
    #           msg = Message()
    #           msg["content-type"] = content_type
    #           charset = msg.get_param("charset")  # returns None if not present
    #
    # Step 2: If charset is still None, look for <meta charset="..."> in the raw bytes.
    #         Use a small regex on response.content (bytes) to avoid a chicken-and-egg
    #         problem — you can't fully parse HTML without knowing the encoding.
    #         Pattern to match both forms:
    #           <meta charset="utf-8">
    #           <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    #
    # Step 3: If still None, fall back to response.apparent_encoding
    #         (chardet/charset-normalizer's statistical guess from the raw bytes).
    #
    # Step 4: Decode response.content (bytes) using the detected charset.
    #         Use errors="replace" so malformed bytes don't crash the crawl:
    #           return response.content.decode(charset, errors="replace")
    msg = Message()
    msg["content-type"] = content_type
    charset = msg.get_param("charset")
    if not charset:
        match = re.search(rb'charset=["\']?([\w-]+)', response.content[:1024])
        if match:
            charset = match.group(1).decode("ascii")
    if not charset:
        charset = response.apparent_encoding
    return (response.content.decode(charset, errors="replace"), response.url)
