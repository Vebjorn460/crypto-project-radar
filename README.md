# Crypto Project Radar

Crypto Project Radar is a daily watchlist scanner for crypto projects with early momentum. It fetches CoinGecko market data, stores local daily snapshots, compares current data with older snapshots, and prints a top-20 radar report.

This is not a trading bot. It does not execute trades and does not provide financial advice.

## What It Tracks

- Current market-cap rank
- Market cap
- 24h volume
- 7d price change
- 30d price change when CoinGecko provides it
- Volume/market-cap ratio
- Rank movement over 7 and 30 days
- Volume growth and short-term consistency

The scanner fetches the top 1000 CoinGecko coins by market cap and excludes the top 100.

## Scoring

Radar score is 0 to 100:

- Rank momentum: 25 points
- Volume growth: 15 points
- Market cap sweet spot: 15 points
- 7d / 30d price momentum: 15 points
- Volume/market cap ratio: 10 points
- Consistency over several days: 10 points
- Risk penalty: up to -20 points for parabolic price moves or unusual volume/market-cap ratios

The default market-cap sweet spot is $10M to $500M.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

The local SQLite database is created at:

```text
data/radar.sqlite3
```

The first run will have limited historical comparisons. Scores become more useful after 7 to 30 days of snapshots.

## Telegram Alerts

Telegram delivery is optional. Set these environment variables:

```bash
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"
python main.py --telegram
```

If either variable is missing, the scanner simply prints the report.

## Configuration

Most settings can be changed with environment variables:

```text
TOP_N_COINS=1000
EXCLUDE_TOP_N=100
MIN_MARKET_CAP_USD=10000000
MAX_MARKET_CAP_USD=500000000
DATABASE_PATH=data/radar.sqlite3
REPORT_LIMIT=20
REQUEST_RETRIES=3
REQUEST_BACKOFF_SECONDS=3
```

## GitHub Actions

The included workflow runs every day at 09:00 UTC and prints the report. To use Telegram from GitHub Actions, add these repository secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Historical comparisons require persisted snapshots. The workflow restores and saves the `data` directory with the GitHub Actions cache and also uploads the SQLite database as an artifact for inspection. For a heavier production setup, use external storage or a dedicated database.
