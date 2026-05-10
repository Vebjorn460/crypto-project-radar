"""CoinGecko API client with conservative retry handling."""

from __future__ import annotations

import time
from typing import Any

import requests

from config import (
    COINGECKO_API_KEY,
    COINGECKO_API_KEY_HEADER,
    COINGECKO_BASE_URL,
    COINS_PER_PAGE,
    REQUEST_BACKOFF_SECONDS,
    REQUEST_PAGE_DELAY_SECONDS,
    REQUEST_RATE_LIMIT_SECONDS,
    REQUEST_RETRIES,
    REQUEST_TIMEOUT_SECONDS,
    TOP_N_COINS,
)


class CoinGeckoError(RuntimeError):
    """Raised when CoinGecko data cannot be fetched safely."""


class CoinGeckoClient:
    def __init__(self, base_url: str = COINGECKO_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "crypto-project-radar/1.0",
            }
        )
        if COINGECKO_API_KEY:
            self.session.headers[COINGECKO_API_KEY_HEADER] = COINGECKO_API_KEY

    def fetch_market_page(self, page: int, per_page: int = COINS_PER_PAGE) -> list[dict[str, Any]]:
        """Fetch one page of USD market data from CoinGecko."""
        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "sparkline": "false",
            "price_change_percentage": "7d,30d",
        }

        last_error = ""

        for attempt in range(1, REQUEST_RETRIES + 1):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait_seconds = _rate_limit_wait_seconds(retry_after, attempt)
                    last_error = f"HTTP 429 rate limited; retrying after {wait_seconds:.1f}s"
                    time.sleep(wait_seconds)
                    continue

                if 500 <= response.status_code < 600:
                    last_error = f"HTTP {response.status_code} from CoinGecko"
                    time.sleep(REQUEST_BACKOFF_SECONDS * attempt)
                    continue

                response.raise_for_status()
                data = response.json()
                if not isinstance(data, list):
                    raise CoinGeckoError("CoinGecko returned an unexpected payload.")
                return data
            except (requests.RequestException, ValueError) as exc:
                last_error = str(exc)
                if attempt == REQUEST_RETRIES:
                    raise CoinGeckoError(f"Failed to fetch CoinGecko market page {page}: {exc}") from exc
                time.sleep(REQUEST_BACKOFF_SECONDS * attempt)

        raise CoinGeckoError(f"Failed to fetch CoinGecko market page {page}: {last_error}")

    def fetch_top_markets(self, limit: int = TOP_N_COINS) -> list[dict[str, Any]]:
        """Fetch the top coins by market cap, up to the configured limit."""
        pages = (limit + COINS_PER_PAGE - 1) // COINS_PER_PAGE
        coins: list[dict[str, Any]] = []

        for page in range(1, pages + 1):
            coins.extend(self.fetch_market_page(page))
            # Keep a delay between pages to reduce rate-limit pressure,
            # especially in GitHub Actions shared runner environments.
            time.sleep(REQUEST_PAGE_DELAY_SECONDS)

        return coins[:limit]


def _rate_limit_wait_seconds(retry_after: str | None, attempt: int) -> float:
    """Respect Retry-After, but enforce a useful minimum when APIs return 0."""
    try:
        header_wait = float(retry_after) if retry_after is not None else 0.0
    except ValueError:
        header_wait = 0.0

    fallback_wait = REQUEST_BACKOFF_SECONDS * attempt
    return max(header_wait, fallback_wait, REQUEST_RATE_LIMIT_SECONDS)
