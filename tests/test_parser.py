"""
Tests for crawler/parser.py.

Write your tests here BEFORE or AS you implement extract_links.
Testing a pure function against known HTML inputs is the fastest
feedback loop you'll ever have. Use it.

Pattern: build a small HTML string, call extract_links, assert on the output.
"""

import pytest
from crawler.parser import extract_links


# --- Example test to show the pattern. Write more like this. ---

def test_extracts_absolute_link():
    html = '<html><body><a href="https://example.com/page">link</a></body></html>'
    links = extract_links(html, base_url="https://example.com")
    assert "https://example.com/page" in links


# --- Tests you should write yourself (remove the skip when ready) ---

@pytest.mark.skip(reason="implement this")
def test_resolves_relative_link():
    # A relative href like "/about" should be resolved against base_url
    html = '<a href="/about">About</a>'
    links = extract_links(html, base_url="https://example.com")
    assert "https://example.com/about" in links


@pytest.mark.skip(reason="implement this")
def test_strips_fragment():
    # https://example.com/page#section should become https://example.com/page
    html = '<a href="https://example.com/page#section">link</a>'
    links = extract_links(html, base_url="https://example.com")
    assert "https://example.com/page" in links
    assert "https://example.com/page#section" not in links


@pytest.mark.skip(reason="implement this")
def test_ignores_mailto_links():
    html = '<a href="mailto:someone@example.com">email</a>'
    links = extract_links(html, base_url="https://example.com")
    assert links == []


@pytest.mark.skip(reason="implement this")
def test_empty_page_returns_empty_list():
    links = extract_links("", base_url="https://example.com")
    assert links == []
