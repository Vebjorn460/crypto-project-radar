"""SQLite snapshot storage for daily radar runs."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from config import DATABASE_PATH


class SnapshotStore:
    def __init__(self, path: Path = DATABASE_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.ensure_schema()

    def ensure_schema(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                snapshot_date TEXT NOT NULL,
                coin_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                rank INTEGER,
                market_cap REAL,
                volume_24h REAL,
                price_change_7d REAL,
                price_change_30d REAL,
                volume_market_cap_ratio REAL,
                PRIMARY KEY (snapshot_date, coin_id)
            )
            """
        )
        self.connection.commit()

    def save_snapshot(self, snapshot_date: date, coins: list[dict[str, Any]]) -> None:
        rows = []
        for coin in coins:
            market_cap = _to_float(coin.get("market_cap"))
            volume = _to_float(coin.get("total_volume"))
            rows.append(
                (
                    snapshot_date.isoformat(),
                    coin.get("id"),
                    (coin.get("symbol") or "").upper(),
                    coin.get("name") or coin.get("id"),
                    _to_int(coin.get("market_cap_rank")),
                    market_cap,
                    volume,
                    _to_float(coin.get("price_change_percentage_7d_in_currency")),
                    _to_float(coin.get("price_change_percentage_30d_in_currency")),
                    _safe_ratio(volume, market_cap),
                )
            )

        self.connection.executemany(
            """
            INSERT OR REPLACE INTO snapshots (
                snapshot_date,
                coin_id,
                symbol,
                name,
                rank,
                market_cap,
                volume_24h,
                price_change_7d,
                price_change_30d,
                volume_market_cap_ratio
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.connection.commit()

    def latest_snapshot(self, snapshot_date: date) -> list[dict[str, Any]]:
        cursor = self.connection.execute(
            "SELECT * FROM snapshots WHERE snapshot_date = ? ORDER BY rank ASC",
            (snapshot_date.isoformat(),),
        )
        return [_row_to_dict(row) for row in cursor.fetchall()]

    def previous_for_coin(self, coin_id: str, before_date: date, days_back: int) -> dict[str, Any] | None:
        """Return the nearest snapshot at least days_back days before before_date."""
        cursor = self.connection.execute(
            """
            SELECT *
            FROM snapshots
            WHERE coin_id = ?
              AND snapshot_date <= date(?, ?)
            ORDER BY snapshot_date DESC
            LIMIT 1
            """,
            (coin_id, before_date.isoformat(), f"-{days_back} days"),
        )
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None

    def recent_for_coin(self, coin_id: str, before_date: date, max_days: int = 7) -> list[dict[str, Any]]:
        cursor = self.connection.execute(
            """
            SELECT *
            FROM snapshots
            WHERE coin_id = ?
              AND snapshot_date < ?
              AND snapshot_date >= date(?, ?)
            ORDER BY snapshot_date ASC
            """,
            (coin_id, before_date.isoformat(), before_date.isoformat(), f"-{max_days} days"),
        )
        return [_row_to_dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        self.connection.close()


def _safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)

