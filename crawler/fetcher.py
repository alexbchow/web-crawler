"""
HTTP fetching.

Fetches a URL using a caller-provided requests.Session and returns the
decoded HTML body. Raises on non-2xx responses, timeouts, and non-HTML
content types.
"""

import re
from email.message import Message

from requests import Session


class NonHTMLResponseError(Exception):
    """Raised when a response Content-Type is not text/html."""


def fetch(url: str, session: Session) -> tuple[str, str]:
    """Fetch a URL and return its decoded HTML content and final URL.

    Args:
        url: The URL to fetch.
        session: A requests.Session to use for the request.

    Returns:
        A tuple of (decoded_html, final_url) where final_url is the URL
        after following any redirects.

    Raises:
        NonHTMLResponseError: if the response Content-Type is not text/html.
        requests.exceptions.HTTPError: on 4xx/5xx responses.
        requests.exceptions.Timeout: if connect or read exceeds timeout.
        requests.exceptions.ConnectionError: on DNS failure or refused connection.
        requests.exceptions.TooManyRedirects: if redirect limit is exceeded.
    """
    response = session.get(url, timeout=(3, 30))
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    if "text/html" not in content_type:
        raise NonHTMLResponseError(f"{url} returned Content-Type: {content_type!r}")

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
