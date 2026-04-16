from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode

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

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "ref",
    "source",
}


def is_nofollow_page(html: str) -> bool:
    soup = BeautifulSoup(html, "lxml")
    for meta_tag in soup.find_all("meta", attrs={"name": "robots"}):
        if "nofollow" in meta_tag.get("content", "") or "noindex" in meta_tag.get(
            "content", ""
        ):
            return True
    return False


def normalize(url: str) -> str:
    """Canonicalize a URL so that equivalent URLs map to the same string.

    Called by extract_links before appending to results. The frontier
    relies on string equality for deduplication, so two URLs that point
    to the same page must produce identical strings after normalization.

    Steps to implement (in order):
      1. You already have: parsed_url = urlparse(url) and lowercased
         scheme + netloc into domain and scheme variables.

      2. Strip tracking query params from parsed_url.query:
           - Call parse_qs(parsed_url.query, keep_blank_values=True)
             This gives you a dict of {param: [value, ...]}
           - Define a set of params to remove:
             {"utm_source", "utm_medium", "utm_campaign", "utm_term",
              "utm_content", "fbclid", "gclid", "ref", "source"}
           - Filter the dict: {k: v for k, v in params.items() if k not in TRACKING_PARAMS}
           - Rebuild the query string with urlencode(filtered, doseq=True)
             Pass sorted=True or sort the keys manually so param order is consistent.
             Add parse_qs and urlencode to your imports from urllib.parse.

      3. Strip trailing slash from the path if:
           - the path ends with "/" AND
           - the path is not just "/" (keep the root)
           - the query string is empty (don't strip if there are params)
           Use parsed_url.path.rstrip("/") or a simple conditional.

      4. Reconstruct using urlunparse with the updated components:
           urlunparse((scheme, domain, new_path, parsed_url.params,
                       new_query, ""))
         Note: pass empty string for fragment — already stripped in extract_links
         but normalize should be safe to call standalone too.

    Args:
        url: An absolute URL (scheme + host already resolved).

    Returns:
        The normalized URL string.
    """

    parsed_url = urlparse(url)
    domain, scheme, query, path = (
        parsed_url.netloc.lower(),
        parsed_url.scheme.lower(),
        parsed_url.query,
        parsed_url.path,
    )
    parsed_query = parse_qs(query, keep_blank_values=True)
    filtered_query = {k: v for k, v in parsed_query.items() if k not in TRACKING_PARAMS}
    reconstructed_query = urlencode(sorted(filtered_query.items()), doseq=True)
    if path != "/" and not reconstructed_query:
        path = path.rstrip("/")
    normalized_url = urlunparse(
        (scheme, domain, path, parsed_url.params, reconstructed_query, "")
    )
    return normalized_url


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
    canonical = soup.find("link", rel = "canonical")
    if canonical and canonical.get("href"):
        return normalize(canonical["href"])
    for link in soup.find_all("a", href=True):  # find all a tags in html
        if "nofollow" in link.get("rel", []):
            continue
        joined_url = urljoin(base_url, link["href"])  # find all links, join to base url
        parsed_url = urlparse(joined_url)  # parse url
        if parsed_url.scheme in ("http", "https"):  # allowlist for scheme
            normalized_url = normalize(joined_url)
            urls.append(normalized_url)
    return urls
