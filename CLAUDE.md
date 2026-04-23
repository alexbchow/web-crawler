# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (uses venv at .venv/)
source .venv/bin/activate

# Run all tests
pytest

# Run a single test
pytest tests/test_parser.py::test_strips_fragment

# Format code
black .

# Run the fetcher manually
python -m crawler.fetcher
```

## Architecture

Single-threaded, synchronous web crawler built in Python across four modules:

1. **`crawler/parser.py`**
   - `extract_links(html, base_url)` — finds all `<a href>` tags via BeautifulSoup, resolves relative URLs, filters to `http`/`https`, skips `rel="nofollow"` links, normalizes each URL before returning
   - `normalize(url)` — strips tracking params (`utm_*`, `fbclid`, etc.), sorts query params, strips trailing slash (root `/` preserved), lowercases scheme and host
   - `is_nofollow_page(html)` — returns `True` if the page has `<meta name="robots" content="nofollow|noindex">`; used by crawler to skip link extraction entirely

2. **`crawler/fetcher.py`**
   - `fetch(url, session) -> (html, final_url)` — uses caller-provided `Session`, applies `(3, 30)` connect/read timeouts, calls `raise_for_status()`, raises `NonHTMLResponseError` for non-`text/html` responses
   - Encoding detection: checks `Content-Type` header charset first, falls back to `<meta charset>` regex scan on raw bytes (first 1024 bytes only), then `response.apparent_encoding`
   - Returns `(decoded_html, response.url)` — final URL after redirects included for dedup
   - Known issues: `Content-Type: None` not guarded (`.get("Content-Type", "")` needed); stale TODO comment block above encoding implementation; typo in `Raises:` docstring (`exceptiosn`)

3. **`crawler/frontier.py`**
   - `Frontier(db_path, resume)` — `deque` + `seen` set backed by SQLite (`frontier.db`); WAL mode enabled
   - SQLite tables: `seen(url TEXT PRIMARY KEY)` (completed), `queue(url TEXT, added_at TIMESTAMP)` (pending)
   - `add()` writes through to `queue` table immediately; `record_fetch()` moves URL from `queue` → `seen`
   - `resume=True` reloads both tables into memory on startup; `resume=False` wipes both tables for a clean crawl
   - `is_allowed(url, user_agent)` — fetches and caches `robots.txt` per domain via `urllib.robotparser`; defaults to allow if unreachable
   - `seconds_until_allowed(url, user_agent)` + `record_fetch(url)` — enforces per-domain crawl delay; respects `Crawl-delay` directive from `robots.txt` if present, falls back to 1s default

4. **`crawler/crawler.py`**
   - `Crawler(seed_url, max_pages, domain, resume)` — owns the `Session` with User-Agent header; optional `domain` restricts crawl to seed domain only
   - `run()` — registers SIGINT handler that sets `_shutdown` flag; loop checks flag each iteration for graceful exit
   - Full crawl loop: scope check → robots.txt check → crawl delay → fetch → redirect dedup → nofollow check → link extraction → frontier
   - Granular exception handling: `NonHTMLResponseError`, `Timeout`, `ConnectionError`, `TooManyRedirects`, `HTTPError`, catch-all `Exception`

5. **`crawler/storage.py`**
   - `store_page(url, html, bucket, s3_client)` — encodes HTML to UTF-8, computes SHA-256 content hash, builds object key `{domain}/{hash[:2]}/{hash}.json.gz`, gzip-compresses a JSON payload (`url`, `fetched_at`, `content_hash`, `html`), and uploads via `s3_client.put_object`
   - S3 client created once in `Crawler.__init__` and passed in; upload failures are caught and logged as warnings without stopping the crawl

6. **`crawler/__main__.py`** — CLI entry point via `python -m crawler <seed_url> [--max-pages N] [--domain DOMAIN] [--resume] [--s3-bucket BUCKET]`

**Tests:** `tests/test_parser.py` (extract_links + normalize), `tests/test_frontier.py` (dedup, ordering, crawl delay), `tests/test_frontier_persistence.py` (SQLite write-through, resume), `tests/test_crawler.py` (mocked fetch/session, SIGINT shutdown), `tests/test_fetcher.py` (encoding detection, content-type filtering)

## Roadmap

### Phase 1 — working crawler ✓ COMPLETE

Get a single-threaded, in-memory crawler running end-to-end.

- [x] **fetcher.py**: timeout `(3, 30)`, User-Agent header, `raise_for_status()`, session passed in from `Crawler`
- [x] **frontier.py**: `set` + `deque`, deduplication correct, `is_empty()` simplified
- [x] **parser.py**: `extract_links` implemented and tested, scheme allowlist fixed to `('http', 'https')`
- [x] **crawler.py**: crawl loop, session ownership in `__init__`, error logging, print progress, entry point
- [x] **tests**: `tests/test_parser.py`, `tests/test_frontier.py`, and `tests/test_crawler.py` complete
- [x] **verified**: end-to-end crawl on `http://books.toscrape.com` working
- [x] **exception policy**: `Raises:` section in `fetcher.py` docstring documents `HTTPError`, `Timeout`, `ConnectionError`
- [x] **CLI entry point**: `python -m crawler <seed_url>` using `argparse` with `--max-pages` flag

---

### Phase 2 — correctness & politeness ✓ COMPLETE

Make the crawler a good citizen before scaling it up.

- [x] **robots.txt** (RFC 9309): `Frontier.is_allowed()` fetches, caches, and checks `robots.txt`; called in `Crawler.run()` before every fetch
- [x] **Per-domain rate limiting**: 1s default delay enforced via `last_fetched` dict; `Crawl-delay` from `robots.txt` respected when present via `rp.crawl_delay(user_agent)`
- [x] **URL normalization hardening**: strip tracking params, sort query params, strip trailing slash (with root guard), lowercase scheme/host; `normalize()` called from `extract_links`
- [x] **Content-type filtering**: `HEAD` or check `Content-Type` header before downloading; skip non-`text/html` responses
- [x] **Redirect handling**: follow up to N redirects (default 10); add final URL to seen-set to avoid re-crawling redirect targets
- [x] **Encoding detection**: read charset from `Content-Type` header first; fall back to `charset-normalizer` for body sniffing
- [x] **Canonical URL**: extract `<link rel="canonical">` and treat it as the authoritative URL for dedup
- [x] **nofollow / noindex**: `is_nofollow_page()` checks page-level meta robots; link-level `rel="nofollow"` skipped in `extract_links`
- [x] **Scope control**: `--domain` flag restricts crawl to seed domain only
- [x] **Structured logging**: all `print` replaced with `logging`; per-module loggers; `basicConfig` in `__main__.py`
- [x] **tests**: `tests/test_fetcher.py` covers encoding detection and content-type filtering with mocked responses

---

### Phase 3 — persistence & resumability (current focus)

Survive crashes; produce usable output. Use **AWS S3** for object storage (free tier: 5GB storage, 20k GET requests/month).

- [x] **Persistent frontier**: back `Frontier` with SQLite (`frontier.db`) — two tables: `seen(url TEXT PRIMARY KEY)` and `queue(url, added_at)`; write-through on every `add()` and `record_fetch()`
- [x] **Graceful shutdown**: SIGINT handler sets `_shutdown` flag; crawl loop exits cleanly after current URL finishes
- [x] **Checkpointing**: `--resume` flag reloads `seen` and `queue` tables into memory on startup
- [x] **Content store → AWS S3**: `crawler/storage.py` with `store_page(url, html, bucket, s3_client)`; gzip-compressed JSON objects; key = `{domain}/{sha256[:2]}/{sha256}.json.gz`; boto3 S3 client created once in `Crawler.__init__`; upload errors logged as warnings without stopping the crawl
- [x] **`--s3-bucket` CLI flag**: pass bucket name at runtime; storage is skipped if flag is omitted
- [x] **tests**: `tests/test_frontier_persistence.py` covers write-through, resume, and fresh-start wipe; `tests/test_crawler.py` covers shutdown flag and SIGINT signal
- [x] **Dedup by content hash**: compute SHA-256 of HTML body before uploading; check if key already exists in S3 (`head_object`) and skip upload if so
- [x] **Config file**: `config.yaml` (seed URLs, max_pages, domain scope, delay, S3 bucket, output path) loaded via `PyYAML`; CLI flags override config
- [x] **Structured logging**: emit one JSON log line per crawled URL (`url`, `status`, `elapsed_ms`, `links_found`, `stored`)

---

### Phase 4 — multithreaded concurrency

Scale I/O throughput while preserving per-domain politeness.

- [ ] **Thread-safe frontier**: add `threading.Lock` around all `Frontier` mutations; use `queue.Queue` instead of `deque` for blocking `next()` across threads
- [ ] **Shared `requests.Session` per thread**: use `threading.local()` to give each thread its own session for connection pooling
- [ ] **`ThreadPoolExecutor` fetch loop**: replace the serial loop in `Crawler.run()` with a pool (default 10 workers); each worker pulls from frontier, fetches, stores to S3, and enqueues discovered links
- [ ] **Per-domain semaphore**: cap concurrent connections to any single domain (default 2) regardless of pool size
- [ ] **Domain-partitioned back-queues**: maintain one `deque` per domain inside `Frontier`; a scheduler thread selects the next domain whose crawl-delay has elapsed (prevents multiple threads hammering the same host)
- [ ] **Progress display**: `tqdm` progress bar with pages crawled, queue depth, pages/sec, and S3 objects written
- [ ] **tests**: concurrency tests asserting no duplicate URLs fetched under parallel execution; use `pytest-httpserver` as a mock origin

---

### Phase 5 — async I/O

Higher throughput with lower resource usage than threads.

- [ ] **Rewrite fetcher with `httpx[async]`**: `async def fetch(url, client)` returning HTML string; same timeout, UA, and exception policy as sync version
- [ ] **Streaming responses**: stream response bodies and abort if `Content-Type` is not `text/html` before reading the full body
- [ ] **Async per-domain rate limiting**: one `asyncio.Lock` + timestamp per domain; `await asyncio.sleep(delay)` without blocking the event loop
- [ ] **`asyncio`-based crawl loop**: replace `ThreadPoolExecutor` with `asyncio.TaskGroup`; bounded concurrency via `asyncio.Semaphore(max_workers)`
- [ ] **Async S3 writes**: use `aioboto3` (async wrapper around `boto3`) so S3 uploads don't block the event loop
- [ ] **DNS caching**: `aiodns` resolver to avoid redundant DNS lookups at high concurrency
- [ ] **CLI overhaul**: replace `argparse` with `typer` + `rich` for colored output, a live stats table, and `--dry-run` mode

---

### Phase 6 — priority frontier & near-duplicate detection

Make the crawler smarter about which URLs to visit and which pages are genuinely new.

- [ ] **Priority scoring**: add a `priority REAL` column to the SQLite `queue` table; score URLs at enqueue time based on in-link count (proxy for PageRank), domain freshness, and URL depth; `next()` pops the highest-scoring URL rather than FIFO
- [ ] **Iterative PageRank**: after each crawl batch, compute a lightweight in-memory PageRank over the link graph (URL → outbound links stored in SQLite); use scores to re-prioritize the remaining queue
- [ ] **SimHash near-duplicate detection**: compute a 64-bit SimHash of each page's text content before storing; compare against stored hashes using Hamming distance ≤ 3 to detect near-duplicates; skip S3 upload and mark as duplicate in the seen table
- [ ] **SimHash store**: persist SimHash values in a new SQLite table `hashes(url TEXT PRIMARY KEY, simhash INTEGER)`; load into a sorted list at startup for fast Hamming distance queries using bit manipulation
- [ ] **Exact-duplicate dedup**: keep SHA-256 content hash check in `store_page` (`head_object` on S3) as a fast pre-filter before the more expensive SimHash comparison

---

### Phase 7 — Redis for shared state

Introduce **Redis** (free, open source) so multiple crawler processes can share frontier and rate-limit state.

- [ ] **Docker Compose**: add `docker-compose.yml` with a `redis` service (port 6379); single `docker compose up` starts the full local stack (S3 is remote via AWS)
- [ ] **Redis-backed frontier**: replace SQLite with Redis using `redis-py`; use a Redis `ZSET` (sorted set, score = priority) for the pending queue and a `SET` for seen URLs; atomic `ZADD` + `SISMEMBER` operations replace the in-process lock
- [ ] **Redis robots.txt cache**: store parsed `robots.txt` per domain as a Redis string with a 24 h TTL (`SET domain:robots <rules> EX 86400`) so all workers share the same cache
- [ ] **Distributed rate limiting via Redis**: use a Redis sorted set (`domain:last_fetch`) keyed by domain with score = last fetch timestamp; workers atomically check and update this before fetching, enforcing crawl delay across processes
- [ ] **Bloom filter via RedisBloom**: use the `RedisBloom` module (`BF.ADD` / `BF.EXISTS`) for memory-efficient distributed dedup — replaces the in-process `seen` set; false-positive rate ~0.1%
- [ ] **Migrate SimHash store to Redis**: move the SimHash table to a Redis hash (`HSET simhashes <url> <hash>`) so all workers share duplicate detection state
- [ ] **Horizontal scaling**: launch N identical crawler processes pointing at the same Redis and S3 bucket; no coordination code needed beyond the shared Redis state
- [ ] **Prometheus metrics**: each worker exposes a `/metrics` endpoint via `prometheus_client` with gauges for pages/sec, duplicate rate, error rate, Redis queue depth, active workers, S3 objects written

---

### Phase 8 — Kafka for decoupled pipeline

Introduce **Apache Kafka** (free, open source via Docker) to decouple fetching, parsing, and storage into independent services.

- [ ] **Add Kafka to Docker Compose**: add `zookeeper` + `kafka` services (or use KRaft mode to skip Zookeeper); expose broker on `localhost:9092`; use `confluentinc/cp-kafka` image
- [ ] **Three topics**:
  - `discovered-urls` — newly found links published by parsers; frontier service consumes and deduplicates
  - `raw-pages` — fetched HTML published by fetchers; parser and storage consumers read from this
  - `crawl-events` — one event per fetch (url, status, elapsed_ms, error); feeds monitoring
- [ ] **Fetcher service** (`services/fetcher.py`): consumes URLs from `discovered-urls` (via `aiokafka`), fetches HTML, publishes raw page to `raw-pages` and fetch event to `crawl-events`
- [ ] **Parser service** (`services/parser.py`): consumes `raw-pages`, extracts links, publishes discovered URLs back to `discovered-urls`; stateless and horizontally scalable
- [ ] **Storage service** (`services/storage.py`): consumes `raw-pages`, writes gzip-compressed JSON to S3 `raw-pages` bucket; deduplicates by SHA-256 before writing
- [ ] **Frontier service** (`services/frontier_service.py`): consumes `discovered-urls`, deduplicates via RedisBloom, enforces per-domain rate limits via Redis, publishes crawlable URLs back to `discovered-urls` with a delay
- [ ] **Consumer groups**: fetcher and storage services each use a separate Kafka consumer group so they independently process `raw-pages` at their own pace
- [ ] **Backpressure**: if the `discovered-urls` topic lag grows too large, the frontier service pauses publishing to fetchers until lag drains

---

### Phase 9 — observability & analytics

Make the system inspectable and queryable at scale.

- [ ] **Prometheus metrics**: each worker exposes a `/metrics` endpoint via `prometheus_client`; add `prometheus` to Docker Compose
- [ ] **Grafana dashboard**: add `grafana` to Docker Compose; import a dashboard showing pages/sec, error rate, Kafka consumer lag, S3 objects written, Redis memory usage
- [ ] **Kafka UI**: add `provectuslabs/kafka-ui` to Docker Compose for visual inspection of topics, consumer groups, and message throughput
- [ ] **Parquet export**: add a batch job (`jobs/export_parquet.py`) that reads stored JSON from S3 and writes partitioned Parquet files (`s3://processed/year=YYYY/month=MM/`) using `pyarrow`; enables SQL queries via DuckDB
- [ ] **DuckDB analytics**: run ad-hoc queries over the Parquet export with DuckDB (free, in-process) for domain coverage reports, error rate breakdowns, and crawl velocity over time
