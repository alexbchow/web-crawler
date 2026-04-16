"""
Tests for crawler/parser.py.

Write your tests here BEFORE or AS you implement extract_links.
Testing a pure function against known HTML inputs is the fastest
feedback loop you'll ever have. Use it.

Pattern: build a small HTML string, call extract_links, assert on the output.
"""

import pytest
from crawler.parser import extract_links, normalize


# --- Example test to show the pattern. Write more like this. ---


def test_extracts_absolute_link():
    html = '<html><body><a href="https://example.com/page">link</a></body></html>'
    links = extract_links(html, base_url="https://example.com")
    assert "https://example.com/page" in links


# --- Tests you should write yourself (remove the skip when ready) ---


def test_resolves_relative_link():
    # A relative href like "/about" should be resolved against base_url
    html = '<a href="/about">About</a>'
    links = extract_links(html, base_url="https://example.com")
    assert "https://example.com/about" in links


def test_strips_fragment():
    # https://example.com/page#section should become https://example.com/page
    html = '<a href="https://example.com/page#section">link</a>'
    links = extract_links(html, base_url="https://example.com")
    assert "https://example.com/page" in links
    assert "https://example.com/page#section" not in links


def test_ignores_mailto_links():
    html = '<a href="mailto:someone@example.com">email</a>'
    links = extract_links(html, base_url="https://example.com")
    assert links == []


def test_empty_page_returns_empty_list():
    links = extract_links("", base_url="https://example.com")
    assert links == []


def test_ignores_javascript_void_links():
    html = '<a href="javascript:void(0)">click me</a>'
    links = extract_links(html, base_url="https://example.com")
    assert links == []


# --- normalize() tests ---


def test_normalize_strips_utm_source():
    url = "https://example.com/page?utm_source=twitter"
    assert normalize(url) == "https://example.com/page"


def test_normalize_strips_all_tracking_params():
    url = "https://example.com/page?utm_source=twitter&utm_medium=social&fbclid=abc&gclid=xyz"
    assert normalize(url) == "https://example.com/page"


def test_normalize_preserves_non_tracking_params():
    url = "https://example.com/search?q=python&page=2"
    assert normalize(url) == "https://example.com/search?page=2&q=python"


def test_normalize_strips_tracking_keeps_non_tracking():
    url = "https://example.com/page?utm_source=twitter&q=hello"
    assert normalize(url) == "https://example.com/page?q=hello"


def test_normalize_sorts_query_params():
    url1 = "https://example.com/page?b=2&a=1"
    url2 = "https://example.com/page?a=1&b=2"
    assert normalize(url1) == normalize(url2)


def test_normalize_strips_trailing_slash():
    url = "https://example.com/about/"
    assert normalize(url) == "https://example.com/about"


def test_normalize_preserves_root_slash():
    url = "https://example.com/"
    assert normalize(url) == "https://example.com/"


def test_normalize_does_not_strip_trailing_slash_with_query():
    url = "https://example.com/about/?q=hello"
    assert normalize(url) == "https://example.com/about/?q=hello"


def test_normalize_strips_fragment():
    url = "https://example.com/page#section"
    assert normalize(url) == "https://example.com/page"


def test_normalize_lowercases_scheme():
    url = "HTTPS://example.com/page"
    assert normalize(url).startswith("https://")


def test_normalize_lowercases_host():
    url = "https://EXAMPLE.COM/page"
    assert normalize(url) == "https://example.com/page"


def test_normalize_already_normalized_url_unchanged():
    url = "https://example.com/page?a=1&b=2"
    assert normalize(url) == url


def test_normalize_strips_fragment_and_tracking_param():
    url = "https://example.com/page?utm_source=twitter&a=1#section"
    assert normalize(url) == "https://example.com/page?a=1"
