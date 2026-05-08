"""
Phase 0.1: Fetch
================

Production-grade HTTP fetcher for the ingestion pipeline.
Fetches raw HTML from 7 whitelisted Groww URLs with:
- ETag conditional fetch (skip if not modified)
- Anti-bot TLS fingerprinting via curl_cffi
- Exponential backoff retry
- Circuit breaker
- Strict URL whitelist enforcement

Architecture reference: Section 4, Phase 0.1
Enforcement: E1 (URL whitelist), ETag validation, redirects disabled
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import httpx

# Optional: curl_cffi for anti-bot TLS fingerprinting
try:
    from curl_cffi import requests as curl_requests

    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False

# =============================================================================
# Configuration (override via env vars or .env file)
# =============================================================================

FETCH_MAX_RETRIES = int(os.getenv("FETCH_MAX_RETRIES", "3"))
FETCH_RETRY_DELAY_SECONDS = int(os.getenv("FETCH_RETRY_DELAY_SECONDS", "5"))
FETCH_TIMEOUT_SECONDS = int(os.getenv("FETCH_TIMEOUT_SECONDS", "30"))
FETCH_CIRCUIT_BREAKER_THRESHOLD = int(os.getenv("FETCH_CIRCUIT_BREAKER_THRESHOLD", "5"))
FETCH_CIRCUIT_BREAKER_TIMEOUT_SECONDS = int(
    os.getenv("FETCH_CIRCUIT_BREAKER_TIMEOUT_SECONDS", "300")
)
FETCH_USER_AGENT = os.getenv(
    "FETCH_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
)

DATA_RAW_HTML = Path(os.getenv("DATA_RAW_HTML", "./data/0_raw_html"))
ETAG_CACHE_FILE = DATA_RAW_HTML / "etag_cache.json"

CONFIG_FILE = Path(os.getenv("CONFIG_FILE", "./data/config.json"))

def load_whitelisted_urls() -> List[str]:
    """Load URLs from config.json or use fallback defaults."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                urls = config.get("fund_urls", [])
                if urls:
                    return urls
        except Exception as exc:
            logger.warning(f"Failed to load config file: {exc}")
    
    # Fallback default URLs
    return [
        "https://groww.in/mutual-funds/the-wealth-company-small-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-ethical-fund-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-multi-asset-allocation-fund-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-flexi-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-gold-etf-fof-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-liquid-fund-direct-growth",
        "https://groww.in/mutual-funds/the-wealth-company-arbitrage-fund-direct-growth",
    ]

# Whitelist (DOC-001 through DOC-007)
WHITELISTED_URLS: List[str] = load_whitelisted_urls()

# =============================================================================
# Logging
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("phase_0_1_fetch")


# =============================================================================
# Data Models
# =============================================================================


class FetchStatus(str, Enum):
    SUCCESS = "success"
    NOT_MODIFIED = "not_modified"
    FAILED = "failed"
    CIRCUIT_OPEN = "circuit_open"
    BLOCKED = "blocked"


@dataclass
class FetchResult:
    url: str
    status: FetchStatus
    doc_id: str = ""
    html: Optional[str] = None
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    http_status: Optional[int] = None
    headers: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None
    fetched_at: str = ""
    duration_ms: float = 0.0
    bytes_downloaded: int = 0


# =============================================================================
# Circuit Breaker
# =============================================================================


class CircuitBreakerOpenError(Exception):
    pass


class CircuitBreaker:
    """
    Simple in-memory circuit breaker.
    Opens after `failure_threshold` consecutive failures.
    Closes automatically after `timeout_seconds`.
    """

    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 300):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed | open | half_open

    def call(self, func, *args, **kwargs):
        if self.state == "open":
            if self.last_failure_time and (
                (time.time() - self.last_failure_time) > self.timeout_seconds
            ):
                logger.info("Circuit breaker entering half-open state")
                self.state = "half_open"
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise exc

    def _on_success(self):
        self.failure_count = 0
        self.state = "closed"

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            logger.error(f"Circuit breaker OPENED after {self.failure_count} failures")
            self.state = "open"


# =============================================================================
# ETag Cache
# =============================================================================


class ETagCache:
    """
    File-based ETag cache for conditional HTTP fetching.
    Stores {url: {"etag": "...", "last_modified": "..."}} mapping.
    """

    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self._cache: Dict[str, Dict[str, str]] = {}
        self._load()

    def _load(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded ETag cache with {len(self._cache)} entries")
            except Exception as exc:
                logger.warning(f"Failed to load ETag cache: {exc}")
                self._cache = {}
        else:
            self._cache = {}

    def _save(self):
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, indent=2)

    def get(self, url: str) -> Dict[str, str]:
        return self._cache.get(url, {})

    def update(
        self, url: str, etag: Optional[str] = None, last_modified: Optional[str] = None
    ):
        if url not in self._cache:
            self._cache[url] = {}
        if etag:
            self._cache[url]["etag"] = etag
        if last_modified:
            self._cache[url]["last_modified"] = last_modified
        self._save()

    def clear(self):
        self._cache = {}
        self._save()


# =============================================================================
# URL Whitelist Validator
# =============================================================================


def validate_url_whitelist(url: str) -> bool:
    """
    Enforcement E1: URL must be in the immutable whitelist.
    Redirects are disabled by never following them.
    """
    if url not in WHITELISTED_URLS:
        logger.error(f"URL NOT IN WHITELIST: {url}")
        return False
    parsed = urlparse(url)
    if parsed.scheme != "https":
        logger.error(f"URL must use HTTPS: {url}")
        return False
    return True


def get_doc_id(url: str) -> str:
    """Map URL to doc_id (DOC-001 through DOC-007)."""
    try:
        idx = WHITELISTED_URLS.index(url)
        return f"DOC-{idx + 1:03d}"
    except ValueError:
        return "DOC-UNKNOWN"


# =============================================================================
# HTTP Fetcher with Anti-Bot & Retry
# =============================================================================


class HTTPFetcher:
    """
    Production-grade HTTP fetcher with:
    - curl_cffi anti-bot TLS fingerprinting (fallback to httpx)
    - Exponential backoff retry
    - Circuit breaker protection
    - ETag conditional requests
    """

    def __init__(
        self,
        max_retries: int = FETCH_MAX_RETRIES,
        retry_delay: int = FETCH_RETRY_DELAY_SECONDS,
        timeout: int = FETCH_TIMEOUT_SECONDS,
        user_agent: str = FETCH_USER_AGENT,
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.user_agent = user_agent
        self.circuit = CircuitBreaker(
            failure_threshold=FETCH_CIRCUIT_BREAKER_THRESHOLD,
            timeout_seconds=FETCH_CIRCUIT_BREAKER_TIMEOUT_SECONDS,
        )
        self.etag_cache = ETagCache(ETAG_CACHE_FILE)

        # Standard anti-bot headers
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    def _fetch_with_httpx(
        self,
        url: str,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
    ) -> FetchResult:
        """Fetch using httpx (standard, no TLS fingerprint spoofing)."""
        request_headers = dict(self.headers)
        if etag:
            request_headers["If-None-Match"] = etag
        if last_modified:
            request_headers["If-Modified-Since"] = last_modified

        start = time.perf_counter()
        with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
            response = client.get(url, headers=request_headers)
            duration_ms = (time.perf_counter() - start) * 1000

            if response.status_code == 304:
                return FetchResult(
                    url=url,
                    status=FetchStatus.NOT_MODIFIED,
                    http_status=304,
                    headers=dict(response.headers),
                    duration_ms=duration_ms,
                )

            response.raise_for_status()
            html = response.text
            return FetchResult(
                url=url,
                status=FetchStatus.SUCCESS,
                html=html,
                etag=response.headers.get("etag"),
                last_modified=response.headers.get("last-modified"),
                http_status=response.status_code,
                headers=dict(response.headers),
                duration_ms=duration_ms,
                bytes_downloaded=len(html.encode("utf-8")),
            )

    def _fetch_with_curl_cffi(
        self,
        url: str,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
    ) -> FetchResult:
        """Fetch using curl_cffi for anti-bot TLS fingerprinting."""
        request_headers = dict(self.headers)
        if etag:
            request_headers["If-None-Match"] = etag
        if last_modified:
            request_headers["If-Modified-Since"] = last_modified

        start = time.perf_counter()
        response = curl_requests.get(
            url,
            headers=request_headers,
            timeout=self.timeout,
            impersonate="chrome124",
            allow_redirects=False,
        )
        duration_ms = (time.perf_counter() - start) * 1000

        if response.status_code == 304:
            return FetchResult(
                url=url,
                status=FetchStatus.NOT_MODIFIED,
                http_status=304,
                headers=dict(response.headers),
                duration_ms=duration_ms,
            )

        response.raise_for_status()
        html = response.text
        return FetchResult(
            url=url,
            status=FetchStatus.SUCCESS,
            html=html,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
            http_status=response.status_code,
            headers=dict(response.headers),
            duration_ms=duration_ms,
            bytes_downloaded=len(html.encode("utf-8")),
        )

    def _fetch_single(self, url: str) -> FetchResult:
        """Single fetch attempt with ETag conditional check."""
        cached = self.etag_cache.get(url)
        etag = cached.get("etag")
        last_modified = cached.get("last_modified")

        try:
            if CURL_CFFI_AVAILABLE:
                logger.debug(f"Using curl_cffi for {url}")
                result = self._fetch_with_curl_cffi(url, etag, last_modified)
            else:
                logger.debug(f"Using httpx for {url}")
                result = self._fetch_with_httpx(url, etag, last_modified)

            # Update ETag cache on success
            if result.status == FetchStatus.SUCCESS:
                self.etag_cache.update(url, result.etag, result.last_modified)

            return result

        except httpx.HTTPStatusError as exc:
            return FetchResult(
                url=url,
                status=FetchStatus.FAILED,
                http_status=exc.response.status_code,
                error=(
                    f"HTTP {exc.response.status_code}: " f"{exc.response.reason_phrase}"
                ),
            )
        except Exception as exc:
            return FetchResult(
                url=url,
                status=FetchStatus.FAILED,
                error=str(exc),
            )

    def fetch_with_retry(self, url: str) -> FetchResult:
        """
        Fetch with exponential backoff retry and circuit breaker.
        """
        if not validate_url_whitelist(url):
            return FetchResult(
                url=url,
                status=FetchStatus.BLOCKED,
                error="URL not in whitelist (Enforcement E1)",
            )

        for attempt in range(1, self.max_retries + 1):
            try:
                result = self.circuit.call(self._fetch_single, url)
                if result.status == FetchStatus.SUCCESS:
                    logger.info(
                        f"Fetched {url} in {result.duration_ms:.0f}ms "
                        f"({result.bytes_downloaded} bytes)"
                    )
                    return result
                if result.status == FetchStatus.NOT_MODIFIED:
                    logger.info(f"Not modified (304): {url}")
                    return result
                # Failed but retryable
                if attempt < self.max_retries:
                    delay = min(self.retry_delay * (2 ** (attempt - 1)), 60)
                    logger.warning(
                        f"Attempt {attempt}/{self.max_retries} failed for {url}: "
                        f"{result.error}. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries} attempts failed for {url}: "
                        f"{result.error}"
                    )
                    return result

            except CircuitBreakerOpenError:
                logger.error(f"Circuit breaker OPEN for {url}")
                return FetchResult(
                    url=url,
                    status=FetchStatus.CIRCUIT_OPEN,
                    error="Circuit breaker is open",
                )
            except Exception as exc:
                if attempt < self.max_retries:
                    delay = min(self.retry_delay * (2 ** (attempt - 1)), 60)
                    logger.warning(
                        f"Attempt {attempt}/{self.max_retries} exception for {url}: "
                        f"{exc}. Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries} attempts failed for {url}: {exc}"
                    )
                    return FetchResult(
                        url=url,
                        status=FetchStatus.FAILED,
                        error=str(exc),
                    )

        return FetchResult(
            url=url,
            status=FetchStatus.FAILED,
            error="Unexpected end of retry loop",
        )

    def fetch_all(self) -> List[FetchResult]:
        """
        Fetch all 7 whitelisted URLs sequentially.
        Single-threaded to avoid triggering anti-bot measures.
        """
        results: List[FetchResult] = []
        logger.info(f"Starting fetch for {len(WHITELISTED_URLS)} whitelisted URLs")

        for url in WHITELISTED_URLS:
            result = self.fetch_with_retry(url)
            result.doc_id = get_doc_id(url)
            result.fetched_at = datetime.now(timezone.utc).isoformat()
            results.append(result)

            # Small jittered delay between fetches to avoid rate limiting
            if url != WHITELISTED_URLS[-1]:
                jitter = 1.0 + (hash(url) % 20) / 10.0  # 1.0 - 2.9s
                logger.debug(f"Sleeping {jitter:.1f}s before next fetch")
                time.sleep(jitter)

        return results


# =============================================================================
# Persistence
# =============================================================================


def save_raw_html(results: List[FetchResult], output_dir: Path) -> Dict[str, Any]:
    """
    Save fetched HTML to disk and return a manifest.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": datetime.now(timezone.utc).isoformat(),
        "total_urls": len(WHITELISTED_URLS),
        "successful": 0,
        "not_modified": 0,
        "failed": 0,
        "results": [],
    }

    for result in results:
        entry = {
            "url": result.url,
            "doc_id": result.doc_id,
            "status": result.status.value,
            "fetched_at": result.fetched_at,
            "duration_ms": round(result.duration_ms, 2),
            "bytes_downloaded": result.bytes_downloaded,
            "error": result.error,
        }
        manifest["results"].append(entry)

        if result.status == FetchStatus.SUCCESS and result.html:
            filename = f"{result.doc_id}.html"
            filepath = output_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(result.html)
            logger.info(f"Saved {filepath} ({result.bytes_downloaded} bytes)")
            manifest["successful"] += 1
        elif result.status == FetchStatus.NOT_MODIFIED:
            manifest["not_modified"] += 1
        else:
            manifest["failed"] += 1
            logger.error(f"Fetch FAILED for {result.doc_id}: {result.error}")

    # Save manifest
    manifest_path = output_dir / "fetch_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Manifest saved to {manifest_path}")

    return manifest


# =============================================================================
# Main Entry Point
# =============================================================================


def run_fetch_phase() -> Dict[str, Any]:
    """
    Execute Phase 0.1 Fetch.
    Returns manifest dict with success/failure counts.

    Failure handling per architecture:
    - Any failure is logged as FETCH_FAILED
    - Previous corpus is retained (not overwritten on failure)
    """
    logger.info("=" * 60)
    logger.info("PHASE 0.1: FETCH")
    logger.info("=" * 60)

    fetcher = HTTPFetcher()
    results = fetcher.fetch_all()
    manifest = save_raw_html(results, DATA_RAW_HTML)

    # Summary
    logger.info("-" * 60)
    logger.info(
        f"Fetch complete: {manifest['successful']} success, "
        f"{manifest['not_modified']} not modified, "
        f"{manifest['failed']} failed"
    )
    if manifest["failed"] > 0:
        logger.warning("Some fetches failed. Previous corpus will be retained.")
    logger.info("=" * 60)

    return manifest


if __name__ == "__main__":
    run_fetch_phase()
