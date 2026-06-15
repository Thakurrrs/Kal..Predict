"""SQLite-backed durable store for paper trading artifacts."""

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kal_predict.models import Decision


class PaperStore:
    """Durable paper trading storage with idempotent writes."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        """Create paper trading tables and indexes if they do not exist."""
        with self._connect() as connection:
            self._create_schema(connection)

    def table_names(self) -> set[str]:
        """Return user table names in the database."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        return {row[0] for row in rows}

    def count_rows(self, table_name: str) -> int:
        """Count rows in a known table."""
        if table_name not in self.table_names():
            raise ValueError(f"unknown table: {table_name}")
        with self._connect() as connection:
            row = connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return int(row[0])

    def record_decision(self, decision: Decision) -> str:
        """Insert a decision once by decision_id."""
        with self._connect() as connection:
            return self._record_decision(connection, decision)

    def record_fill(self, fill: dict[str, Any]) -> str:
        """Insert one paper fill per decision."""
        self._validate_fill(fill)
        with self._connect() as connection:
            return self._record_fill(connection, fill)

    def record_decision_and_fill(self, decision: Decision, fill: dict[str, Any]) -> None:
        """Atomically record a decision and fill."""
        self._validate_fill(fill)
        with self._connect() as connection:
            self._record_decision(connection, decision)
            self._record_fill(connection, fill)

    def record_outcome(
        self,
        fill_id: str,
        outcome_id: str,
        status: str,
        resolved_at: str,
    ) -> dict[str, Any]:
        """Record a paper fill outcome and realized PnL once."""
        with self._connect() as connection:
            fill = self._get_fill(connection, fill_id)
            net_pnl = self._calculate_fill_pnl(fill, status)
            counts_as_resolved_trade = status in {"won", "lost"}
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO outcomes (
                    outcome_id, fill_id, market_id, status, net_pnl,
                    payload_json, resolved_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    outcome_id,
                    fill_id,
                    fill["market_id"],
                    status,
                    net_pnl,
                    json.dumps(
                        {
                            "outcome_id": outcome_id,
                            "fill_id": fill_id,
                            "status": status,
                            "net_pnl": net_pnl,
                            "counts_as_resolved_trade": counts_as_resolved_trade,
                        }
                    ),
                    resolved_at,
                ),
            )
        return {
            "write_status": "inserted" if cursor.rowcount == 1 else "ignored",
            "net_pnl": net_pnl,
            "counts_as_resolved_trade": counts_as_resolved_trade,
        }

    def unresolved_exposure(self) -> float:
        """Return notional of paper fills without outcomes."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COALESCE(SUM(f.fill_price * f.size), 0)
                FROM paper_fills f
                LEFT JOIN outcomes o ON o.fill_id = f.fill_id
                WHERE o.fill_id IS NULL
                """
            ).fetchone()
        return round(float(row[0]), 10)

    def realized_net_pnl(self) -> float:
        """Return realized net PnL from unique outcomes."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(net_pnl), 0) FROM outcomes"
            ).fetchone()
        return round(float(row[0]), 10)

    def paper_metrics(self) -> dict[str, Any]:
        """Return durable paper trading metrics for UI reporting."""
        with self._connect() as connection:
            fill_row = connection.execute(
                """
                SELECT COUNT(*), MAX(timestamp)
                FROM paper_fills
                """
            ).fetchone()
            outcome_row = connection.execute(
                """
                SELECT
                    COALESCE(SUM(net_pnl), 0),
                    SUM(CASE WHEN status = 'won' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN status = 'lost' THEN 1 ELSE 0 END)
                FROM outcomes
                """
            ).fetchone()
            risk_row = connection.execute(
                """
                SELECT COUNT(*)
                FROM decisions
                WHERE json_extract(payload_json, '$.risk_gate_result') = 'FAIL'
                """
            ).fetchone()

        return {
            "paper_pnl": round(float(outcome_row[0]), 2),
            "wins": int(outcome_row[1] or 0),
            "losses": int(outcome_row[2] or 0),
            "total_trades": int(fill_row[0] or 0),
            "risk_gate_failures": int(risk_row[0] or 0),
            "last_trade_at": fill_row[1],
            "unresolved_exposure": round(self.unresolved_exposure(), 2),
        }

    def record_observation(self, observation: dict[str, Any]) -> str:
        """Insert one observation, idempotent per (scan_id, market_id).

        Observations are read-only instrumentation records: what the router saw
        for a market during a scan. They never affect trading logic. Re-running
        the same scan_id over the same market is a no-op; the same market in a
        new scan creates a new row (this is how daily volume accumulates).
        """
        self._validate_observation(observation)
        observation_id = self._observation_id(
            observation["scan_id"], observation["market_id"]
        )
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO observations (
                    observation_id, scan_id, market_id, category, subcategory,
                    parser_status, enabled_for_paper, market_implied_prob, spread,
                    volume, liquidity, close_time, hours_to_close, market_status,
                    observed_at, payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    observation_id,
                    observation["scan_id"],
                    observation["market_id"],
                    observation["category"],
                    observation.get("subcategory"),
                    observation["parser_status"],
                    1 if observation.get("enabled_for_paper") else 0,
                    observation.get("market_implied_prob"),
                    observation.get("spread"),
                    observation.get("volume"),
                    observation.get("liquidity"),
                    observation.get("close_time"),
                    observation.get("hours_to_close"),
                    observation.get("market_status"),
                    observation.get("observed_at")
                    or datetime.now(timezone.utc).isoformat(),
                    json.dumps(observation),
                ),
            )
        return "inserted" if cursor.rowcount == 1 else "ignored"

    def observation_category_summary(self) -> list[dict[str, Any]]:
        """Aggregate observation counts by category/subcategory/parser_status.

        This is the raw input for the Phase 4 throughput report.
        """
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT category, subcategory, parser_status, COUNT(*)
                FROM observations
                GROUP BY category, subcategory, parser_status
                ORDER BY category, subcategory, parser_status
                """
            ).fetchall()
        return [
            {
                "category": row[0],
                "subcategory": row[1],
                "parser_status": row[2],
                "count": int(row[3]),
            }
            for row in rows
        ]

    def _validate_observation(self, observation: dict[str, Any]) -> None:
        required = ("scan_id", "market_id", "category", "parser_status")
        for field in required:
            value = observation.get(field)
            if value is None or value == "":
                raise ValueError(f"missing observation field: {field}")

    @staticmethod
    def _observation_id(scan_id: str, market_id: str) -> str:
        digest = hashlib.sha256(f"{scan_id}|{market_id}".encode("utf-8")).hexdigest()
        return digest[:32]

    def observation_throughput(self) -> dict[str, Any]:
        """Summarize observation volume per category for the throughput report.

        Returns, per category (and the soccer subcategory), the number of
        distinct days observed, total observations, and the resulting average
        observations per day. This is the binding number for deciding whether
        downstream model phases are worth building per category.
        """
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    category,
                    subcategory,
                    COUNT(*) AS total,
                    COUNT(DISTINCT substr(observed_at, 1, 10)) AS days,
                    SUM(CASE WHEN parser_status = 'supported' THEN 1 ELSE 0 END)
                        AS supported,
                    SUM(enabled_for_paper) AS paper_enabled
                FROM observations
                GROUP BY category, subcategory
                ORDER BY total DESC
                """
            ).fetchall()
            span = connection.execute(
                "SELECT MIN(substr(observed_at, 1, 10)), MAX(substr(observed_at, 1, 10)), "
                "COUNT(*) FROM observations"
            ).fetchone()

        categories = []
        for row in rows:
            total = int(row[2])
            days = int(row[3]) or 1
            categories.append(
                {
                    "category": row[0],
                    "subcategory": row[1],
                    "total_observations": total,
                    "distinct_days": int(row[3]),
                    "avg_per_day": round(total / days, 2),
                    "supported": int(row[4] or 0),
                    "paper_enabled": int(row[5] or 0),
                }
            )

        return {
            "first_day": span[0],
            "last_day": span[1],
            "total_observations": int(span[2] or 0),
            "categories": categories,
        }

    def _record_decision(self, connection: sqlite3.Connection, decision: Decision) -> str:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO decisions (
                decision_id, market_id, trace_id, payload_json, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                decision.decision_id,
                decision.market_id,
                decision.trace_id,
                decision.model_dump_json(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        return "inserted" if cursor.rowcount == 1 else "ignored"

    def _record_fill(self, connection: sqlite3.Connection, fill: dict[str, Any]) -> str:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO paper_fills (
                fill_id, decision_id, market_id, side, fill_price, size,
                fees, timestamp, trace_id, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fill["fill_id"],
                fill["decision_id"],
                fill["market_id"],
                fill["side"],
                fill["fill_price"],
                fill["size"],
                fill["fees"],
                fill["timestamp"],
                fill["trace_id"],
                json.dumps(fill),
            ),
        )
        return "inserted" if cursor.rowcount == 1 else "ignored"

    def _validate_fill(self, fill: dict[str, Any]) -> None:
        required = (
            "fill_id",
            "decision_id",
            "market_id",
            "side",
            "fill_price",
            "size",
            "fees",
            "timestamp",
            "trace_id",
        )
        for field in required:
            if field not in fill or fill[field] is None or fill[field] == "":
                raise ValueError(f"missing fill field: {field}")

    def _get_fill(self, connection: sqlite3.Connection, fill_id: str) -> dict[str, Any]:
        row = connection.execute(
            """
            SELECT fill_id, decision_id, market_id, side, fill_price, size,
                   fees, timestamp, trace_id
            FROM paper_fills
            WHERE fill_id = ?
            """,
            (fill_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"unknown fill_id: {fill_id}")
        return {
            "fill_id": row[0],
            "decision_id": row[1],
            "market_id": row[2],
            "side": row[3],
            "fill_price": float(row[4]),
            "size": int(row[5]),
            "fees": float(row[6]),
            "timestamp": row[7],
            "trace_id": row[8],
        }

    def _calculate_fill_pnl(self, fill: dict[str, Any], status: str) -> float:
        if status == "won":
            pnl = (1.0 - fill["fill_price"]) * fill["size"] - fill["fees"]
        elif status == "lost":
            pnl = -(fill["fill_price"] * fill["size"]) - fill["fees"]
        elif status == "canceled":
            pnl = 0.0
        else:
            raise ValueError(f"unsupported outcome status: {status}")
        return round(float(pnl), 10)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    def _create_schema(self, connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS research_snapshots (
                research_snapshot_id TEXT PRIMARY KEY,
                market_id TEXT NOT NULL,
                trace_id TEXT,
                category TEXT,
                payload_json TEXT NOT NULL,
                retrieved_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS decisions (
                decision_id TEXT PRIMARY KEY,
                market_id TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS paper_fills (
                fill_id TEXT PRIMARY KEY,
                decision_id TEXT NOT NULL UNIQUE,
                market_id TEXT NOT NULL,
                side TEXT NOT NULL,
                fill_price REAL NOT NULL,
                size INTEGER NOT NULL,
                fees REAL NOT NULL,
                timestamp TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS outcomes (
                outcome_id TEXT PRIMARY KEY,
                fill_id TEXT NOT NULL UNIQUE,
                market_id TEXT NOT NULL,
                status TEXT NOT NULL,
                net_pnl REAL,
                payload_json TEXT NOT NULL,
                resolved_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS market_skips (
                skip_id TEXT PRIMARY KEY,
                scan_id TEXT NOT NULL,
                market_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                trace_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS observations (
                observation_id TEXT PRIMARY KEY,
                scan_id TEXT NOT NULL,
                market_id TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                parser_status TEXT NOT NULL,
                enabled_for_paper INTEGER NOT NULL,
                market_implied_prob REAL,
                spread REAL,
                volume INTEGER,
                liquidity REAL,
                close_time TEXT,
                hours_to_close REAL,
                market_status TEXT,
                observed_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS performance_daily (
                day TEXT PRIMARY KEY,
                gross_pnl REAL NOT NULL DEFAULT 0,
                net_pnl REAL NOT NULL DEFAULT 0,
                fees REAL NOT NULL DEFAULT 0,
                resolved_trades INTEGER NOT NULL DEFAULT 0,
                unresolved_exposure REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS source_cache (
                source TEXT NOT NULL,
                cache_key TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                PRIMARY KEY (source, cache_key)
            );

            CREATE INDEX IF NOT EXISTS idx_decisions_trace_id ON decisions(trace_id);
            CREATE INDEX IF NOT EXISTS idx_decisions_market_id ON decisions(market_id);
            CREATE INDEX IF NOT EXISTS idx_paper_fills_market_id ON paper_fills(market_id);
            CREATE INDEX IF NOT EXISTS idx_paper_fills_decision_id
                ON paper_fills(decision_id);
            CREATE INDEX IF NOT EXISTS idx_outcomes_market_id ON outcomes(market_id);
            CREATE INDEX IF NOT EXISTS idx_market_skips_market_reason
                ON market_skips(market_id, reason);
            CREATE INDEX IF NOT EXISTS idx_observations_scan ON observations(scan_id);
            CREATE INDEX IF NOT EXISTS idx_observations_category
                ON observations(category, subcategory);
            CREATE INDEX IF NOT EXISTS idx_observations_observed_at
                ON observations(observed_at);
            """
        )
