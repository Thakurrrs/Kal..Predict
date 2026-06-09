"""SQLite-backed durable store for paper trading artifacts."""

import json
import sqlite3
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
                decision.trace_id,
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
            if not fill.get(field):
                raise ValueError(f"missing fill field: {field}")

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
            """
        )
