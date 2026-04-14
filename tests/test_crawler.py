"""
Tests for crawler/crawler.py.

Strategy: mock fetch() and extract_links() at the crawler module level so
tests run without network access. The real Frontier is used throughout —
its deduplication behaviour is part of what we're testing here.

Patch targets:
  crawler.crawler.Session        — prevents a real Session from being created
                                   in __init__; autouse so every test is covered
  crawler.crawler.fetch          — controls what HTML is "returned"
  crawler.crawler.extract_links  — controls what links are "found"
"""

import pytest
from unittest.mock import patch, call, MagicMock
from crawler.crawler import Crawler


@pytest.fixture(autouse=True)
def mock_session():
    """Prevent Crawler.__init__ from opening a real requests.Session."""
    with patch("crawler.crawler.Session"):
        yield


SEED = "https://example.com"
PAGE_A = "https://example.com/a"
PAGE_B = "https://example.com/b"
FAKE_HTML = "<html></html>"


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def test_init_accepts_seed_and_max_pages():
    # Should not raise; just verifies the constructor signature is correct.
    crawler = Crawler(seed_url=SEED, max_pages=10)
    assert crawler is not None


def test_init_default_max_pages_is_50():
    crawler = Crawler(seed_url=SEED)
    assert crawler.max_pages == 50


# ---------------------------------------------------------------------------
# Basic crawl loop
# ---------------------------------------------------------------------------

def test_run_fetches_seed_url():
    with patch("crawler.crawler.fetch", return_value=FAKE_HTML) as mock_fetch, \
         patch("crawler.crawler.extract_links", return_value=[]):
        Crawler(seed_url=SEED, max_pages=1).run()
        mock_fetch.assert_called_once_with(SEED)


def test_run_passes_html_and_base_url_to_extract_links():
    with patch("crawler.crawler.fetch", return_value=FAKE_HTML), \
         patch("crawler.crawler.extract_links", return_value=[]) as mock_extract:
        Crawler(seed_url=SEED, max_pages=1).run()
        mock_extract.assert_called_once_with(FAKE_HTML, SEED)


def test_run_adds_discovered_links_to_frontier_and_crawls_them():
    # Seed returns PAGE_A as a link; PAGE_A returns no links.
    fetch_responses = {SEED: FAKE_HTML, PAGE_A: FAKE_HTML}
    extract_responses = {SEED: [PAGE_A], PAGE_A: []}

    with patch("crawler.crawler.fetch", side_effect=lambda url: fetch_responses[url]) as mock_fetch, \
         patch("crawler.crawler.extract_links", side_effect=lambda html, url: extract_responses[url]):
        Crawler(seed_url=SEED, max_pages=10).run()

    fetched = [c.args[0] for c in mock_fetch.call_args_list]
    assert SEED in fetched
    assert PAGE_A in fetched


def test_run_crawls_multiple_discovered_links():
    fetch_responses = {SEED: FAKE_HTML, PAGE_A: FAKE_HTML, PAGE_B: FAKE_HTML}
    extract_responses = {SEED: [PAGE_A, PAGE_B], PAGE_A: [], PAGE_B: []}

    with patch("crawler.crawler.fetch", side_effect=lambda url: fetch_responses[url]) as mock_fetch, \
         patch("crawler.crawler.extract_links", side_effect=lambda html, url: extract_responses[url]):
        Crawler(seed_url=SEED, max_pages=10).run()

    fetched = [c.args[0] for c in mock_fetch.call_args_list]
    assert set(fetched) == {SEED, PAGE_A, PAGE_B}


# ---------------------------------------------------------------------------
# Termination conditions
# ---------------------------------------------------------------------------

def test_run_stops_when_frontier_is_empty():
    # Seed discovers no links → frontier empties after one fetch.
    with patch("crawler.crawler.fetch", return_value=FAKE_HTML) as mock_fetch, \
         patch("crawler.crawler.extract_links", return_value=[]):
        Crawler(seed_url=SEED, max_pages=100).run()

    assert mock_fetch.call_count == 1


def test_run_stops_after_max_pages():
    # Every page keeps discovering a new URL, but max_pages caps the crawl.
    counter = {"n": 0}

    def fake_extract(html, url):
        counter["n"] += 1
        return [f"https://example.com/page-{counter['n']}"]

    with patch("crawler.crawler.fetch", return_value=FAKE_HTML) as mock_fetch, \
         patch("crawler.crawler.extract_links", side_effect=fake_extract):
        Crawler(seed_url=SEED, max_pages=5).run()

    assert mock_fetch.call_count == 5


def test_run_with_max_pages_one_only_fetches_seed():
    with patch("crawler.crawler.fetch", return_value=FAKE_HTML) as mock_fetch, \
         patch("crawler.crawler.extract_links", return_value=[PAGE_A, PAGE_B]):
        Crawler(seed_url=SEED, max_pages=1).run()

    assert mock_fetch.call_count == 1
    assert mock_fetch.call_args == call(SEED)


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def test_run_does_not_fetch_same_url_twice():
    # Seed and PAGE_A both link back to SEED — should only be fetched once.
    fetch_responses = {SEED: FAKE_HTML, PAGE_A: FAKE_HTML}
    extract_responses = {SEED: [PAGE_A, SEED], PAGE_A: [SEED]}

    with patch("crawler.crawler.fetch", side_effect=lambda url: fetch_responses[url]) as mock_fetch, \
         patch("crawler.crawler.extract_links", side_effect=lambda html, url: extract_responses[url]):
        Crawler(seed_url=SEED, max_pages=10).run()

    fetched = [c.args[0] for c in mock_fetch.call_args_list]
    assert fetched.count(SEED) == 1


def test_run_does_not_fetch_seed_again_if_discovered_as_link():
    with patch("crawler.crawler.fetch", return_value=FAKE_HTML) as mock_fetch, \
         patch("crawler.crawler.extract_links", return_value=[SEED]):
        Crawler(seed_url=SEED, max_pages=10).run()

    assert mock_fetch.call_count == 1


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_run_continues_after_fetch_error():
    # Fetching PAGE_A raises; the crawl should still reach PAGE_B.
    def fake_fetch(url):
        if url == PAGE_A:
            raise Exception("connection refused")
        return FAKE_HTML

    extract_responses = {SEED: [PAGE_A, PAGE_B], PAGE_B: []}

    with patch("crawler.crawler.fetch", side_effect=fake_fetch) as mock_fetch, \
         patch("crawler.crawler.extract_links", side_effect=lambda html, url: extract_responses.get(url, [])):
        Crawler(seed_url=SEED, max_pages=10).run()

    fetched = [c.args[0] for c in mock_fetch.call_args_list]
    assert PAGE_B in fetched


def test_run_counts_errored_pages_toward_max_pages():
    # Every fetch raises; max_pages should still bound the number of attempts.
    with patch("crawler.crawler.fetch", side_effect=Exception("timeout")) as mock_fetch, \
         patch("crawler.crawler.extract_links", return_value=[]):
        counter = {"n": 0}
        original_extract = __import__("crawler.crawler", fromlist=["extract_links"])

        # Inject an infinite supply of URLs via extract_links on the error path.
        # Since fetch raises, extract_links won't be called — so we need the
        # frontier pre-populated. Use a subclass to seed extra URLs.
        class PreloadedCrawler(Crawler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                for i in range(20):
                    self.frontier.add(f"https://example.com/p{i}")

        PreloadedCrawler(seed_url=SEED, max_pages=5).run()

    assert mock_fetch.call_count == 5


def test_run_handles_http_error_without_stopping():
    from requests.exceptions import HTTPError
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = HTTPError("404")

    def fake_fetch(url):
        if url == PAGE_A:
            raise HTTPError("404 Not Found")
        return FAKE_HTML

    extract_responses = {SEED: [PAGE_A, PAGE_B], PAGE_B: []}

    with patch("crawler.crawler.fetch", side_effect=fake_fetch) as mock_fetch, \
         patch("crawler.crawler.extract_links", side_effect=lambda html, url: extract_responses.get(url, [])):
        Crawler(seed_url=SEED, max_pages=10).run()

    fetched = [c.args[0] for c in mock_fetch.call_args_list]
    assert PAGE_B in fetched
