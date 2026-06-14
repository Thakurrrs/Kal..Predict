"""Persistent source response cache for research fetchers."""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from kal_predict.models import SourceHealth


@dataclass(frozen=True)
class SourceCacheResult:
    """Result returned from source cache lookups."""

    payload: Any
    cache_hit: bool
    retrieved_at: str
    expires_at: str
    source_health: SourceHealth


class SourceCache:
    """SQLite-backed cache for deterministic source responses."""

    def __init__(self, database_path: str | Path, now: Callable[[], str] | None = None) -> None:
        self.database_path = Path(database_path)
        self._now = now or (lambda: datetime.now(timezone.utc).isoformat())
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    async def get_or_fetch(
        self,
        source: str,
        cache_key: str,
        ttl_seconds: int,
        fetch: Callable[[], Awaitable[Any]],
    ) -> SourceCacheResult:
        """Return cached payload before expiry, otherwise fetch and persist."""
        cached = self._get_cached(source, cache_key)
        now = self._parse_time(self._now())
        if cached is not None:
            payload, retrieved_at, expires_at = cached
            if self._parse_time(expires_at) > now:
                return SourceCacheResult(
                    payload=payload,
                    cache_hit=True,
                    retrieved_at=retrieved_at,
                    expires_at=expires_at,
                    source_health=SourceHealth(
                        source=source,
                        status="ok",
                        latency_ms=0,
                        freshness_seconds=self._freshness_seconds(retrieved_at, now),
                        error_code=None,
                    ),
                )

        payload = await fetch()
        retrieved_at = now.isoformat()
        expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
        self._upsert(source, cache_key, payload, retrieved_at, expires_at)
        return SourceCacheResult(
            payload=payload,
            cache_hit=False,
            retrieved_at=retrieved_at,
            expires_at=expires_at,
            source_health=SourceHealth(
                source=source,
                status="ok",
                latency_ms=0,
                freshness_seconds=0,
                error_code=None,
            ),
        )

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS source_cache (
                    source TEXT NOT NULL,
                    cache_key TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    retrieved_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    PRIMARY KEY (source, cache_key)
                )
                """
            )

    def _get_cached(self, source: str, cache_key: str) -> tuple[Any, str, str] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json, retrieved_at, expires_at
                FROM source_cache
                WHERE source = ? AND cache_key = ?
                """,
                (source, cache_key),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0]), row[1], row[2]

    def _upsert(
        self,
        source: str,
        cache_key: str,
        payload: Any,
        retrieved_at: str,
        expires_at: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO source_cache (
                    source, cache_key, payload_json, retrieved_at, expires_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source, cache_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    retrieved_at = excluded.retrieved_at,
                    expires_at = excluded.expires_at
                """,
                (source, cache_key, json.dumps(payload), retrieved_at, expires_at),
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)

    def _parse_time(self, value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _freshness_seconds(self, retrieved_at: str, now: datetime) -> int:
        return max(0, int((now - self._parse_time(retrieved_at)).total_seconds()))
