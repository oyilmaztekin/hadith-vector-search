"""HTTP utilities with retry and polite rate limiting."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Optional

import requests
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential


class HttpError(RuntimeError):
    """Raised when the HTTP client cannot recover from an error."""


@dataclass
class RateLimiter:
    """Simple per-process rate limiter."""

    min_interval: float = 1.0
    jitter: float = 0.3
    _last_call: Optional[float] = None

    def wait(self) -> None:
        now = time.monotonic()
        if self._last_call is not None:
            elapsed = now - self._last_call
            target = self.min_interval + random.uniform(0, self.jitter)
            if elapsed < target:
                time.sleep(target - elapsed)
        self._last_call = time.monotonic()


class HttpClient:
    """Minimal HTTP client tailored for Sunnah.com scraping."""

    def __init__(self, rate_limiter: RateLimiter | None = None) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "RiyadScraper/0.1 (+https://example.com/contact)",
            "Accept": "text/html,application/xhtml+xml",
        })
        self._rate_limiter = rate_limiter or RateLimiter()

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_random_exponential(multiplier=0.5, max=10),
        retry=retry_if_exception_type((requests.RequestException, HttpError)),
        before_sleep=before_sleep_log(__import__("logging").getLogger(__name__), "Retrying HTTP fetch"),
    )
    def fetch_text(self, url: str, *, timeout: float = 20.0) -> str:
        self._rate_limiter.wait()
        response = self._session.get(url, timeout=timeout)
        if response.status_code >= 500:
            raise HttpError(f"Server error {response.status_code} for {url}")
        if response.status_code >= 400:
            raise HttpError(f"Client error {response.status_code} for {url}")
        response.encoding = response.apparent_encoding or response.encoding
        return response.text

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "HttpClient":  # pragma: no cover - convenience
        return self

    def __exit__(self, *exc_info: object) -> None:  # pragma: no cover - convenience
        self.close()
