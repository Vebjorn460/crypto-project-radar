"""Report rendering and optional Telegram delivery."""

from __future__ import annotations

from datetime import date

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from scoring import ScoredCoin


def render_report(scored: list[ScoredCoin], run_date: date, limit: int) -> str:
    lines = [
        f"Crypto Project Radar - {run_date.isoformat()}",
        "Watchlist only. This is not financial advice and does not execute trades.",
        "",
    ]

    if not scored:
        lines.append("No projects matched the radar criteria today.")
        return "\n".join(lines)

    for index, item in enumerate(scored[:limit], start=1):
        coin = item.coin
        previous_rank = _previous_rank(item)
        lines.extend(
            [
                f"{index}. PROJECT ALERT: {coin['name']} ({coin['symbol']})",
                f"CoinGecko ID: {coin['coin_id']}",
                f"Rank: {previous_rank or 'n/a'} -> {coin.get('rank') or 'n/a'}",
                f"Market cap: {_money(coin.get('market_cap'))}",
                f"24h volume: {_money(coin.get('volume_24h'))}",
                f"7d change: {_percent(coin.get('price_change_7d'))}",
                f"30d change: {_percent(coin.get('price_change_30d'))}",
                f"Volume/market cap: {_ratio(coin.get('volume_market_cap_ratio'))}",
                f"Radar score: {item.score}/100",
                f"Reason: {'; '.join(item.reasons) if item.reasons else 'baseline criteria matched'}",
                "Status: Watchlist only",
                "",
            ]
        )

    return "\n".join(lines).strip()


def send_telegram_alert(message: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message[:4096],
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
    response.raise_for_status()


def _previous_rank(item: ScoredCoin) -> int | None:
    if item.previous_30d and item.previous_30d.get("rank"):
        return item.previous_30d["rank"]
    if item.previous_7d and item.previous_7d.get("rank"):
        return item.previous_7d["rank"]
    return None


def _money(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:.0f}"


def _percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.1f}%"


def _ratio(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"

