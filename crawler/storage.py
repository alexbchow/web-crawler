"""
S3 storage for crawled pages.

Each page is stored as a gzip-compressed JSON object. The object key is
derived from the page's SHA-256 content hash, which also enables
content-based deduplication via head_object checks.
"""

import gzip
import hashlib
import json
from datetime import datetime, timezone
from urllib.parse import urlparse
from botocore.exceptions import ClientError


def store_page(url: str, html: str, bucket: str, s3_client) -> str:
    """Compress and upload a crawled page to S3.

    Args:
        url: The page URL (used to build the object key and stored in payload).
        html: Decoded HTML content of the page.
        bucket: S3 bucket name to upload to.
        s3_client: A boto3 S3 client.

    Returns:
        The S3 object key the page was stored under.
    """
    raw = html.encode("utf-8")
    content_hash = hashlib.sha256(raw).hexdigest()
    domain = urlparse(url).netloc
    key = f"{domain}/{content_hash[:2]}/{content_hash}.json.gz"

    payload = {
        "url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "content_hash": content_hash,
        "html": html,
    }

    compressed = gzip.compress(json.dumps(payload).encode("utf-8"))
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return key
    except ClientError:
        pass

    s3_client.put_object(Bucket=bucket, Key=key, Body=compressed)

    return key
