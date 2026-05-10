"""CLI entry point for Crypto Project Radar."""

from __future__ import annotations

import argparse
from datetime import date

from coingecko_client import CoinGeckoClient
from config import EXCLUDE_TOP_N, MAX_MARKET_CAP_USD, MIN_MARKET_CAP_USD, REPORT_LIMIT
from report import render_report, send_telegram_alert
from scoring import ScoredCoin, score_coin
from storage import SnapshotStore


def run(scan_date: date, send_telegram: bool = False) -> str:
    client = CoinGeckoClient()
    store = SnapshotStore()

    try:
        markets = client.fetch_top_markets()
        eligible = [
            coin
            for coin in markets
            if coin.get("market_cap_rank") and coin["market_cap_rank"] > EXCLUDE_TOP_N
        ]

        store.save_snapshot(scan_date, eligible)
        today = store.latest_snapshot(scan_date)

        scored = []
        for coin in today:
            previous_7d = store.previous_for_coin(coin["coin_id"], scan_date, 7)
            previous_30d = store.previous_for_coin(coin["coin_id"], scan_date, 30)
            recent = store.recent_for_coin(coin["coin_id"], scan_date, 7)
            scored.append(score_coin(coin, previous_7d, previous_30d, recent))

        filtered = [item for item in scored if _matches_alert_criteria(item) and item.score > 0]
        filtered.sort(key=lambda item: item.score, reverse=True)

        report = render_report(filtered, scan_date, REPORT_LIMIT)
        if send_telegram:
            send_telegram_alert(report)
        return report
    finally:
        store.close()


def _matches_alert_criteria(item: ScoredCoin) -> bool:
    """Require actual snapshot evidence before a coin reaches the report."""
    coin = item.coin
    market_cap = coin.get("market_cap")
    if not market_cap or not (MIN_MARKET_CAP_USD <= market_cap <= MAX_MARKET_CAP_USD):
        return False

    if _looks_overextended(coin):
        return False

    return _has_rank_improvement(item) and _has_volume_growth(item)


def _has_rank_improvement(item: ScoredCoin) -> bool:
    current_rank = item.coin.get("rank")
    if not current_rank:
        return False
    previous_ranks = [
        previous.get("rank")
        for previous in (item.previous_7d, item.previous_30d)
        if previous and previous.get("rank")
    ]
    return any(previous_rank > current_rank for previous_rank in previous_ranks)


def _has_volume_growth(item: ScoredCoin) -> bool:
    current_volume = item.coin.get("volume_24h")
    if not current_volume:
        return False
    previous_volumes = [
        previous.get("volume_24h")
        for previous in (item.previous_7d, item.previous_30d)
        if previous and previous.get("volume_24h")
    ]
    return any(current_volume > previous_volume for previous_volume in previous_volumes)


def _looks_overextended(coin: dict) -> bool:
    change_7d = coin.get("price_change_7d")
    change_30d = coin.get("price_change_30d")
    ratio = coin.get("volume_market_cap_ratio")
    return (
        (change_7d is not None and change_7d > 120)
        or (change_30d is not None and change_30d > 300)
        or (ratio is not None and ratio > 1.0)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily watchlist scanner for early crypto project momentum.")
    parser.add_argument("--date", help="Snapshot date in YYYY-MM-DD format. Defaults to today.")
    parser.add_argument("--telegram", action="store_true", help="Send the report to Telegram if env vars are set.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scan_date = date.fromisoformat(args.date) if args.date else date.today()
    print(run(scan_date, send_telegram=args.telegram))


if __name__ == "__main__":
    main()
