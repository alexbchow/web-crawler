from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse

"""
HTML parsing and link extraction.

This is the right place to start. It has no network dependency,
so you can build and test it in isolation before touching fetcher.py.

Key concepts you'll need to understand to implement this:
  - urllib.parse.urljoin: resolves relative URLs against a base
  - urllib.parse.urlparse / urlunparse: decompose and reconstruct URLs
  - BeautifulSoup: find_all('a', href=True) to get anchor tags
  - URL normalization: strip fragments (#section), handle empty hrefs,
    decide which schemes to keep (http/https only?)
"""


def normalize(url: str) -> str:
    """Canonicalize a URL so that equivalent URLs map to the same string.

    Called by extract_links before appending to results. The frontier
    relies on string equality for deduplication, so two URLs that point
    to the same page must produce identical strings after normalization.

    Steps to implement (in order):
      1. Parse with urlparse.
      2. Lowercase the scheme and host (urllib may already do scheme for you).
      3. Strip tracking query params — remove any key matching:
           utm_source, utm_medium, utm_campaign, utm_term, utm_content,
           fbclid, gclid, ref, source
         Use urllib.parse.parse_qs / urlencode to rebuild the query string
         after filtering. Sort remaining params so ?a=1&b=2 == ?b=2&a=1.
      4. Strip trailing slash from the path ONLY if there is no query string.
         (Trailing slash on the root path "/" should be kept.)
      5. Reconstruct with urlunparse and return.

    Args:
        url: An absolute URL (scheme + host already resolved).

    Returns:
        The normalized URL string.
    """
    raise NotImplementedError


def extract_links(html: str, base_url: str) -> list[str]:
    """Parse all hyperlinks out of an HTML page.

    Args:
        html: Raw HTML content of a crawled page.
        base_url: The URL this page was fetched from. Used to resolve
                  relative URLs (e.g. "/about" -> "https://example.com/about").

    Returns:
        A list of absolute URLs found on the page. Duplicates are allowed
        here — deduplication is the frontier's responsibility.
    """
    urls = []
    soup = BeautifulSoup(html, "lxml")
    for link in soup.find_all("a", href=True):  # find all a tags in html
        joined_url = urljoin(base_url, link["href"])  # find all links, join to base url
        parsed_url = urlparse(joined_url)  # parse url
        parsed_url = parsed_url._replace(fragment="")  # remove fragment tags
        if parsed_url.scheme in ("http", "https"):  # allowlist for scheme
            normalized_url = urlunparse(parsed_url)
            urls.append(normalized_url)
    return urls
