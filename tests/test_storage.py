from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from crawler.storage import store_page

FAKE_URL = "https://example.com/page"
FAKE_HTML = "<html><body>hello</body></html>"
BUCKET = "my-crawler-raw-pages"


def make_client():
    return MagicMock()


def client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": ""}}, "HeadObject")


# ---------------------------------------------------------------------------
# Upload behaviour
# ---------------------------------------------------------------------------


def test_new_page_is_uploaded():
    client = make_client()
    client.head_object.side_effect = client_error("404")

    store_page(FAKE_URL, FAKE_HTML, BUCKET, client)

    client.put_object.assert_called_once()


def test_duplicate_page_is_not_uploaded():
    client = make_client()
    client.head_object.return_value = {}  # object already exists

    store_page(FAKE_URL, FAKE_HTML, BUCKET, client)

    client.put_object.assert_not_called()


def test_duplicate_returns_same_key():
    client = make_client()
    client.head_object.return_value = {}

    key1 = store_page(FAKE_URL, FAKE_HTML, BUCKET, client)
    key2 = store_page(FAKE_URL, FAKE_HTML, BUCKET, client)

    assert key1 == key2


# ---------------------------------------------------------------------------
# Object key structure
# ---------------------------------------------------------------------------


def test_key_contains_domain():
    client = make_client()
    client.head_object.side_effect = client_error("404")

    key = store_page(FAKE_URL, FAKE_HTML, BUCKET, client)

    assert key.startswith("example.com/")


def test_key_uses_content_hash_prefix():
    client = make_client()
    client.head_object.side_effect = client_error("404")

    key = store_page(FAKE_URL, FAKE_HTML, BUCKET, client)
    parts = key.split("/")

    # key format: domain/ab/abcdef....json.gz
    assert len(parts) == 3
    assert parts[2].endswith(".json.gz")
    assert parts[1] == parts[2][:2]


def test_different_content_produces_different_keys():
    client = make_client()
    client.head_object.side_effect = client_error("404")

    key1 = store_page(FAKE_URL, "<html>page one</html>", BUCKET, client)
    key2 = store_page(FAKE_URL, "<html>page two</html>", BUCKET, client)

    assert key1 != key2
