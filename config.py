"""Configuration for Crypto Project Radar."""

from __future__ import annotations

import os
from pathlib import Path


COINGECKO_BASE_URL = os.getenv("COINGECKO_BASE_URL", "https://api.coingecko.com/api/v3")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")
COINGECKO_API_KEY_HEADER = os.getenv("COINGECKO_API_KEY_HEADER", "x-cg-demo-api-key")

# CoinGecko allows up to 250 results per page on the markets endpoint.
TOP_N_COINS = int(os.getenv("TOP_N_COINS", "1000"))
EXCLUDE_TOP_N = int(os.getenv("EXCLUDE_TOP_N", "100"))
COINS_PER_PAGE = int(os.getenv("COINS_PER_PAGE", "250"))

MIN_MARKET_CAP_USD = float(os.getenv("MIN_MARKET_CAP_USD", "10000000"))
MAX_MARKET_CAP_USD = float(os.getenv("MAX_MARKET_CAP_USD", "500000000"))

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", DATA_DIR / "radar.sqlite3"))

REPORT_LIMIT = int(os.getenv("REPORT_LIMIT", "20"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
REQUEST_RETRIES = int(os.getenv("REQUEST_RETRIES", "3"))
REQUEST_BACKOFF_SECONDS = float(os.getenv("REQUEST_BACKOFF_SECONDS", "3"))
REQUEST_PAGE_DELAY_SECONDS = float(os.getenv("REQUEST_PAGE_DELAY_SECONDS", "2"))
REQUEST_RATE_LIMIT_SECONDS = float(os.getenv("REQUEST_RATE_LIMIT_SECONDS", "60"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
