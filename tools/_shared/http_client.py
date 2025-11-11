"""HTTP client utilities for content collectors.

Simplified for personal use - basic rate limiting and retry logic.
"""

import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class RateLimitedHttpClient:
    """HTTP client with simple rate limiting and retry logic."""

    def __init__(
        self,
        requests_per_second: float = 1.0,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
    ):
        """
        Initialize rate-limited HTTP client.

        Args:
            requests_per_second: Max requests per second
            timeout: Request timeout in seconds
            max_retries: Max retry attempts
            backoff_factor: Backoff factor for retries
        """
        self.requests_per_second = requests_per_second
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._last_request: float | None = None

        # Session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _rate_limit(self) -> None:
        """Simple sleep-based rate limiting."""
        if self._last_request is None:
            self._last_request = time.time()
            return

        interval = 1.0 / self.requests_per_second
        elapsed = time.time() - self._last_request

        if elapsed < interval:
            time.sleep(interval - elapsed)

        self._last_request = time.time()

    def get(self, url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> requests.Response:
        """GET request with rate limiting and retry."""
        self._rate_limit()
        response = self.session.get(url, params=params, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response

    def post(
        self, url: str, data: dict[str, Any] | None = None, json: dict[str, Any] | None = None, **kwargs: Any
    ) -> requests.Response:
        """POST request with rate limiting."""
        self._rate_limit()
        response = self.session.post(url, data=data, json=json, timeout=self.timeout, **kwargs)
        response.raise_for_status()
        return response

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self) -> "RateLimitedHttpClient":
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        self.close()
