"""Durable tamper-evident event storage."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any

_ZERO_HASH = "0" * 64


class EventIntegrityError(RuntimeError):
    """Raised when the journal cannot be trusted."""


class EventStore:
    """SQLite-backed, per-run hash-chained event journal.

    Each instance owns one connection. Operations are serialized within the
    instance; SQLite transactions serialize file-backed writers across
    processes. Callers must not use ``db`` directly in production code.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(
            self.path, timeout=10, check_same_thread=False, isolation_level=None
        )
        self.db.row_factory = sqlite3.Row
        self._lock = RLock()
        for pragma in (
            "PRAGMA foreign_keys=ON",
            "PRAGMA busy_timeout=10000",
            "PRAGMA synchronous=FULL",
        ):
            self.db.execute(pragma)
        if self.path != ":memory:":
            self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS events (
                run_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                type TEXT NOT NULL,
                payload TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                previous_event_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL,
                PRIMARY KEY (run_id, seq),
                UNIQUE (event_hash)
            )"""
        )

    def close(self) -> None:
        with self._lock:
            self.db.close()

    def __enter__(self) -> "EventStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _hash(previous: str, run_id: str, seq: int, event_type: str, body: str, timestamp: str) -> str:
        return hashlib.sha256(
            f"{previous}|{run_id}|{seq}|{event_type}|{body}|{timestamp}".encode()
        ).hexdigest()

    def append(self, run_id: str, event_type: str, payload: Any, timestamp: str) -> int:
        if not run_id or not event_type or not timestamp:
            raise ValueError("run_id, event_type, and timestamp are required")
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with self._lock:
            try:
                self.db.execute("BEGIN IMMEDIATE")
                row = self.db.execute(
                    "SELECT seq, event_hash FROM events WHERE run_id=? ORDER BY seq DESC LIMIT 1",
                    (run_id,),
                ).fetchone()
                seq = int(row["seq"]) + 1 if row else 1
                previous = str(row["event_hash"]) if row else _ZERO_HASH
                event_hash = self._hash(previous, run_id, seq, event_type, body, timestamp)
                self.db.execute(
                    "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (run_id, seq, event_type, body, timestamp, previous, event_hash),
                )
                self.db.execute("COMMIT")
                return seq
            except (sqlite3.DatabaseError, TypeError, ValueError) as exc:
                try:
                    self.db.execute("ROLLBACK")
                except sqlite3.DatabaseError:
                    pass
                raise EventIntegrityError("event append failed") from exc

    def verify(self, run_id: str) -> bool:
        with self._lock:
            try:
                rows = self.db.execute(
                    "SELECT * FROM events WHERE run_id=? ORDER BY seq", (run_id,)
                ).fetchall()
                previous = _ZERO_HASH
                expected_seq = 1
                for row in rows:
                    if row["seq"] != expected_seq:
                        return False
                    computed = self._hash(
                        previous, row["run_id"], row["seq"], row["type"],
                        row["payload"], row["timestamp"]
                    )
                    if row["previous_event_hash"] != previous or row["event_hash"] != computed:
                        return False
                    previous, expected_seq = computed, expected_seq + 1
                return True
            except (sqlite3.DatabaseError, TypeError, ValueError):
                return False

    def assert_integrity(self, run_id: str) -> None:
        if not self.verify(run_id):
            raise EventIntegrityError(f"event chain is invalid for run {run_id}")

    def events(self, run_id: str) -> list[sqlite3.Row]:
        with self._lock:
            return list(self.db.execute(
                "SELECT * FROM events WHERE run_id=? ORDER BY seq", (run_id,)
            ).fetchall())


__all__ = ["EventStore", "EventIntegrityError"]
