"""Radar scoring model for early crypto project momentum.

The score is a watchlist signal only. It is not financial advice and does not
make trading decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import MAX_MARKET_CAP_USD, MIN_MARKET_CAP_USD


@dataclass(frozen=True)
class ScoredCoin:
    coin: dict[str, Any]
    previous_7d: dict[str, Any] | None
    previous_30d: dict[str, Any] | None
    recent: list[dict[str, Any]]
    score: int
    reasons: list[str]


def score_coin(
    coin: dict[str, Any],
    previous_7d: dict[str, Any] | None,
    previous_30d: dict[str, Any] | None,
    recent: list[dict[str, Any]],
) -> ScoredCoin:
    score = 0.0
    reasons: list[str] = []

    score += _rank_momentum_score(coin, previous_7d, previous_30d, reasons)
    score += _volume_growth_score(coin, previous_7d, previous_30d, reasons)
    score += _market_cap_score(coin, reasons)
    score += _price_momentum_score(coin, reasons)
    score += _volume_market_cap_score(coin, reasons)
    score += _consistency_score(coin, recent, reasons)

    penalty = _risk_penalty(coin, reasons)
    score -= penalty

    return ScoredCoin(
        coin=coin,
        previous_7d=previous_7d,
        previous_30d=previous_30d,
        recent=recent,
        score=max(0, min(100, round(score))),
        reasons=reasons,
    )


def _rank_momentum_score(
    coin: dict[str, Any],
    previous_7d: dict[str, Any] | None,
    previous_30d: dict[str, Any] | None,
    reasons: list[str],
) -> float:
    """Award up to 25 points for improving rank over 7 and 30 days."""
    current_rank = coin.get("rank")
    if not current_rank:
        return 0.0

    points = 0.0
    for previous, max_points, label in ((previous_7d, 10, "7d"), (previous_30d, 15, "30d")):
        previous_rank = previous.get("rank") if previous else None
        if not previous_rank or previous_rank <= current_rank:
            continue

        rank_gain = previous_rank - current_rank
        gain_ratio = rank_gain / previous_rank
        earned = min(max_points, max_points * min(1.0, gain_ratio / 0.35))
        points += earned
        reasons.append(f"rank improved {previous_rank} -> {current_rank} over {label}")

    return points


def _volume_growth_score(
    coin: dict[str, Any],
    previous_7d: dict[str, Any] | None,
    previous_30d: dict[str, Any] | None,
    reasons: list[str],
) -> float:
    """Award up to 15 points for rising 24h volume versus prior snapshots."""
    current_volume = coin.get("volume_24h") or 0
    best_growth = 0.0

    for previous in (previous_7d, previous_30d):
        previous_volume = previous.get("volume_24h") if previous else None
        if previous_volume and previous_volume > 0:
            best_growth = max(best_growth, (current_volume - previous_volume) / previous_volume)

    if best_growth <= 0:
        return 0.0

    reasons.append(f"volume growth +{best_growth * 100:.0f}%")
    return min(15.0, best_growth * 15.0 / 2.0)


def _market_cap_score(coin: dict[str, Any], reasons: list[str]) -> float:
    """Award up to 15 points for the requested $10M-$500M market cap zone."""
    market_cap = coin.get("market_cap")
    if not market_cap:
        return 0.0

    if MIN_MARKET_CAP_USD <= market_cap <= MAX_MARKET_CAP_USD:
        reasons.append("market cap is inside the target early-stage range")
        return 15.0

    if market_cap < MIN_MARKET_CAP_USD:
        return max(0.0, 15.0 * market_cap / MIN_MARKET_CAP_USD)

    if market_cap <= MAX_MARKET_CAP_USD * 1.5:
        return max(0.0, 15.0 * (1.5 - market_cap / MAX_MARKET_CAP_USD) / 0.5)

    return 0.0


def _price_momentum_score(coin: dict[str, Any], reasons: list[str]) -> float:
    """Award up to 15 points for constructive 7d and 30d price momentum."""
    change_7d = coin.get("price_change_7d")
    change_30d = coin.get("price_change_30d")
    points = 0.0

    if change_7d is not None and change_7d > 0:
        points += min(7.0, change_7d / 30.0 * 7.0)
        reasons.append(f"7d price momentum +{change_7d:.1f}%")

    if change_30d is not None and change_30d > 0:
        points += min(8.0, change_30d / 80.0 * 8.0)
        reasons.append(f"30d price momentum +{change_30d:.1f}%")

    return min(15.0, points)


def _volume_market_cap_score(coin: dict[str, Any], reasons: list[str]) -> float:
    """Award up to 10 points for healthy liquidity relative to market cap."""
    ratio = coin.get("volume_market_cap_ratio")
    if ratio is None or ratio <= 0:
        return 0.0

    if 0.03 <= ratio <= 0.35:
        reasons.append(f"volume/market cap ratio {ratio:.2f}")
        return min(10.0, ratio / 0.15 * 10.0)

    if ratio < 0.03:
        return ratio / 0.03 * 4.0

    return max(0.0, 10.0 - min(10.0, (ratio - 0.35) / 0.65 * 10.0))


def _consistency_score(coin: dict[str, Any], recent: list[dict[str, Any]], reasons: list[str]) -> float:
    """Award up to 10 points when recent snapshots show repeated improvement."""
    if len(recent) < 3 or not coin.get("rank"):
        return 0.0

    ranks = [row.get("rank") for row in recent if row.get("rank")]
    volumes = [row.get("volume_24h") for row in recent if row.get("volume_24h")]
    if len(ranks) < 3:
        return 0.0

    improving_rank_days = sum(1 for earlier, later in zip(ranks, ranks[1:]) if later < earlier)
    improving_volume_days = sum(1 for earlier, later in zip(volumes, volumes[1:]) if later > earlier)

    points = min(6.0, improving_rank_days * 2.0) + min(4.0, improving_volume_days * 1.5)
    if points >= 5:
        reasons.append("momentum has persisted across recent snapshots")
    return min(10.0, points)


def _risk_penalty(coin: dict[str, Any], reasons: list[str]) -> float:
    """Subtract up to 20 points for parabolic or suspicious-looking conditions."""
    penalty = 0.0
    change_7d = coin.get("price_change_7d")
    change_30d = coin.get("price_change_30d")
    ratio = coin.get("volume_market_cap_ratio")

    if change_7d is not None and change_7d > 120:
        penalty += 10.0
        reasons.append("risk penalty: 7d move looks parabolic")

    if change_30d is not None and change_30d > 300:
        penalty += 10.0
        reasons.append("risk penalty: 30d move looks overextended")

    if ratio is not None and ratio > 1.0:
        penalty += 10.0
        reasons.append("risk penalty: volume/market cap ratio looks unusual")

    return min(20.0, penalty)

