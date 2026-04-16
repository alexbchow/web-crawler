"""
Tests for encoding detection in crawler/fetcher.py.

Strategy: mock the session and response objects so no network calls are made.
Each test controls exactly what the response looks like (headers, body bytes,
apparent_encoding) and asserts on what fetch() returns.
"""

import pytest
from unittest.mock import MagicMock
from crawler.fetcher import fetch, NonHTMLResponseError


def make_response(
    content_type="text/html",
    content=b"<html></html>",
    url="https://example.com",
    apparent_encoding="utf-8",
):
    """Build a mock response with the given attributes."""
    mock_response = MagicMock()
    mock_response.headers = {"Content-Type": content_type}
    mock_response.content = content
    mock_response.url = url
    mock_response.apparent_encoding = apparent_encoding
    mock_response.raise_for_status.return_value = None
    return mock_response


def make_session(response):
    """Build a mock session that returns the given response."""
    mock_session = MagicMock()
    mock_session.get.return_value = response
    return mock_session


# ---------------------------------------------------------------------------
# Return shape
# ---------------------------------------------------------------------------


def test_fetch_returns_tuple_of_html_and_url():
    response = make_response(content_type="text/html; charset=utf-8")
    html, url = fetch("https://example.com", make_session(response))
    assert isinstance(html, str)
    assert url == "https://example.com"


# ---------------------------------------------------------------------------
# Charset detection — Content-Type header
# ---------------------------------------------------------------------------


def test_charset_from_content_type_header():
    content = "héllo".encode("latin-1")
    response = make_response(
        content_type="text/html; charset=latin-1",
        content=content,
    )
    html, _ = fetch("https://example.com", make_session(response))
    assert "héllo" in html


def test_charset_header_case_insensitive():
    # charset=UTF-8 (uppercase) should work the same as charset=utf-8
    content = "hello".encode("utf-8")
    response = make_response(
        content_type="text/html; charset=UTF-8",
        content=content,
    )
    html, _ = fetch("https://example.com", make_session(response))
    assert "hello" in html


# ---------------------------------------------------------------------------
# Charset detection — <meta charset> tag
# ---------------------------------------------------------------------------


def test_charset_from_meta_charset_tag():
    content = b'<html><head><meta charset="latin-1"></head><body>h\xe9llo</body></html>'
    response = make_response(
        content_type="text/html",  # no charset in header
        content=content,
        apparent_encoding="utf-8",
    )
    html, _ = fetch("https://example.com", make_session(response))
    assert "héllo" in html


def test_charset_from_meta_http_equiv_tag():
    content = (
        b"<html><head>"
        b'<meta http-equiv="Content-Type" content="text/html; charset=latin-1">'
        b"</head><body>h\xe9llo</body></html>"
    )
    response = make_response(
        content_type="text/html",
        content=content,
        apparent_encoding="utf-8",
    )
    html, _ = fetch("https://example.com", make_session(response))
    assert "héllo" in html


def test_meta_charset_without_quotes():
    # <meta charset=utf-8> — no quotes around value
    content = b"<html><head><meta charset=utf-8></head><body>hello</body></html>"
    response = make_response(
        content_type="text/html",
        content=content,
    )
    html, _ = fetch("https://example.com", make_session(response))
    assert "hello" in html


# ---------------------------------------------------------------------------
# Charset detection — apparent_encoding fallback
# ---------------------------------------------------------------------------


def test_fallback_to_apparent_encoding():
    # No charset in header, no meta tag — should use apparent_encoding
    content = "héllo".encode("latin-1")
    response = make_response(
        content_type="text/html",
        content=content,
        apparent_encoding="latin-1",
    )
    html, _ = fetch("https://example.com", make_session(response))
    assert "héllo" in html


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------


def test_malformed_bytes_do_not_crash():
    # bytes that are invalid in utf-8 should be replaced, not raise
    content = b"<html><body>bad byte: \xff\xfe</body></html>"
    response = make_response(
        content_type="text/html; charset=utf-8",
        content=content,
    )
    html, _ = fetch("https://example.com", make_session(response))
    assert isinstance(html, str)  # didn't crash


# ---------------------------------------------------------------------------
# Non-HTML content type
# ---------------------------------------------------------------------------


def test_non_html_content_type_raises():
    response = make_response(content_type="application/pdf")
    with pytest.raises(NonHTMLResponseError):
        fetch("https://example.com/file.pdf", make_session(response))


def test_image_content_type_raises():
    response = make_response(content_type="image/png")
    with pytest.raises(NonHTMLResponseError):
        fetch("https://example.com/image.png", make_session(response))
