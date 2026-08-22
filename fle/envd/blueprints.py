"""Generation-scoped blueprint store.

Blueprints are learned artifacts: agents save reusable factory fragments
during training rollouts and place them by name in later episodes.  Scoping
implements the generation lifecycle decision:

- ``scope=None``      -> ephemeral, dies with the lease (benchmark default;
                         evaluation never sees cross-episode state).
- ``scope="lineage"`` -> durable SQLite rows shared by every rollout in a
                         training generation; fresh generations start clean.

The store never decides fitness.  It only records usage counters; decay and
pruning policies are trainer-side calls.
"""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

BLUEPRINT_STORE_VERSION = "blueprint-store-v1"
MAX_BLUEPRINT_BYTES = 512 * 1024
DEFAULT_MAX_PER_SCOPE = 64
_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS blueprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    entity_count INTEGER NOT NULL DEFAULT 0,
    center_x REAL,
    center_y REAL,
    source TEXT NOT NULL DEFAULT 'agent',
    created_at TEXT NOT NULL,
    created_tick INTEGER,
    times_placed INTEGER NOT NULL DEFAULT 0,
    last_used_tick INTEGER,
    last_used_lease TEXT,
    UNIQUE(scope, name)
);
CREATE INDEX IF NOT EXISTS idx_blueprints_scope ON blueprints(scope);
"""


class BlueprintError(Exception):
    """Base class for blueprint store failures surfaced to the agent."""


class BlueprintQuotaExceeded(BlueprintError):
    pass


class BlueprintNotFound(BlueprintError):
    pass


class BlueprintInvalid(BlueprintError):
    pass


@dataclass
class BlueprintRecord:
    name: str
    content: str
    content_sha256: str
    entity_count: int = 0
    center_x: float | None = None
    center_y: float | None = None
    created_tick: int | None = None
    created_at: str | None = None
    times_placed: int = 0
    last_used_tick: int | None = None
    scope: str | None = None

    def summary(self) -> dict[str, object]:
        return {
            "name": self.name,
            "entity_count": self.entity_count,
            "times_placed": self.times_placed,
            "content_sha256": self.content_sha256[:12],
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_name(name: str) -> str:
    if not isinstance(name, str) or not _NAME_PATTERN.match(name):
        raise BlueprintInvalid(
            f"Invalid blueprint name {name!r}: use 1-64 chars of "
            "[A-Za-z0-9_.-]"
        )
    return name


def _validate_content(content: str) -> tuple[str, str]:
    if not isinstance(content, str) or not content:
        raise BlueprintInvalid("Blueprint content must be a non-empty string")
    if len(content) > MAX_BLUEPRINT_BYTES:
        raise BlueprintInvalid(
            f"Blueprint exceeds {MAX_BLUEPRINT_BYTES} byte limit"
        )
    # Vanilla exchange strings are '0' + base64 payload (+ optional crc).
    if not content.startswith("0"):
        raise BlueprintInvalid("Content is not a Factorio blueprint string")
    digest = hashlib.sha256(content.encode()).hexdigest()
    return content, digest


def default_db_path() -> Path:
    root = Path(os.environ.get("FLE_BLUEPRINT_DB", ".fle/blueprints.db"))
    return root


class BlueprintStore:
    """Durable (SQLite) or ephemeral (in-memory) blueprint storage."""

    def __init__(
        self,
        scope: str | None,
        db_path: Path | str | None = None,
        max_per_scope: int = DEFAULT_MAX_PER_SCOPE,
    ):
        self.scope = scope
        self.max_per_scope = max(1, max_per_scope)
        self._lock = threading.Lock()
        if scope is None:
            self._db_path = None
            self._memory: dict[str, BlueprintRecord] = {}
        else:
            path = Path(db_path) if db_path else default_db_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            self._db_path = path
            with self._connect() as conn:
                conn.executescript(_SCHEMA)

    # -- plumbing -----------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    @property
    def persistent(self) -> bool:
        return self.scope is not None

    # -- CRUD ---------------------------------------------------------------

    def save(
        self,
        name: str,
        content: str,
        *,
        entity_count: int = 0,
        center_x: float | None = None,
        center_y: float | None = None,
        created_tick: int | None = None,
        source: str = "agent",
    ) -> BlueprintRecord:
        _validate_name(name)
        content, digest = _validate_content(content)
        with self._lock:
            count = self.count()
            existing = self._get(name)
            if existing is None and count >= self.max_per_scope:
                raise BlueprintQuotaExceeded(
                    f"Scope {self.scope!r} holds {count} blueprints "
                    f"(limit {self.max_per_scope}); prune or reuse a name"
                )
            record = BlueprintRecord(
                name=name,
                content=content,
                content_sha256=digest,
                entity_count=int(entity_count),
                center_x=center_x,
                center_y=center_y,
                created_tick=created_tick,
                created_at=_now(),
                times_placed=(existing.times_placed if existing else 0),
                last_used_tick=(
                    existing.last_used_tick if existing else None
                ),
                scope=self.scope,
            )
            if self.persistent:
                with self._connect() as conn:
                    conn.execute(
                        """
                        INSERT INTO blueprints (
                            scope, name, content, content_sha256, entity_count,
                            center_x, center_y, source, created_at, created_tick,
                            times_placed, last_used_tick
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(scope, name) DO UPDATE SET
                            content = excluded.content,
                            content_sha256 = excluded.content_sha256,
                            entity_count = excluded.entity_count,
                            center_x = excluded.center_x,
                            center_y = excluded.center_y,
                            created_at = excluded.created_at,
                            created_tick = excluded.created_tick
                        """,
                        (
                            self.scope,
                            name,
                            content,
                            digest,
                            record.entity_count,
                            center_x,
                            center_y,
                            source,
                            _now(),
                            created_tick,
                            record.times_placed,
                            record.last_used_tick,
                        ),
                    )
            else:
                self._memory[name] = record
            return record

    def get(self, name: str) -> BlueprintRecord:
        _validate_name(name)
        with self._lock:
            record = self._get(name)
        if record is None:
            raise BlueprintNotFound(f"No blueprint named {name!r} in scope")
        return record

    def try_get(self, name: str) -> BlueprintRecord | None:
        try:
            return self.get(name)
        except (BlueprintNotFound, BlueprintInvalid):
            return None

    def list_summaries(self) -> list[dict[str, object]]:
        with self._lock:
            records = list(self._memory.values()) if not self.persistent else []
        if self.persistent:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT name, entity_count, times_placed, content_sha256
                    FROM blueprints WHERE scope = ? ORDER BY name
                    """,
                    (self.scope,),
                ).fetchall()
            return [
                {
                    "name": row[0],
                    "entity_count": row[1],
                    "times_placed": row[2],
                    "content_sha256": row[3][:12],
                }
                for row in rows
            ]
        return [record.summary() for record in sorted(
            records, key=lambda r: r.name
        )]

    def count(self) -> int:
        if not self.persistent:
            return len(self._memory)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM blueprints WHERE scope = ?",
                (self.scope,),
            ).fetchone()
        return int(row[0]) if row else 0

    def record_use(self, name: str, tick: int | None, lease_id: str | None = None) -> None:
        with self._lock:
            if not self.persistent:
                record = self._memory.get(name)
                if record is not None:
                    record.times_placed += 1
                    record.last_used_tick = tick
                return
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE blueprints
                    SET times_placed = times_placed + 1,
                        last_used_tick = ?,
                        last_used_lease = ?
                    WHERE scope = ? AND name = ?
                    """,
                    (tick, lease_id, self.scope, name),
                )

    def _get(self, name: str) -> BlueprintRecord | None:
        if not self.persistent:
            return self._memory.get(name)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT name, content, content_sha256, entity_count, center_x,
                       center_y, created_tick, times_placed, last_used_tick
                FROM blueprints WHERE scope = ? AND name = ?
                """,
                (self.scope, name),
            ).fetchone()
        if row is None:
            return None
        return BlueprintRecord(
            name=row[0],
            content=row[1],
            content_sha256=row[2],
            entity_count=row[3],
            center_x=row[4],
            center_y=row[5],
            created_tick=row[6],
            times_placed=row[7],
            last_used_tick=row[8],
            scope=self.scope,
        )

    # -- lifecycle management ----------------------------------------------

    def drop_scope(self) -> int:
        """Delete every blueprint in this scope (generation retirement)."""
        with self._lock:
            if not self.persistent:
                dropped = len(self._memory)
                self._memory.clear()
                return dropped
            with self._connect() as conn:
                cursor = conn.execute(
                    "DELETE FROM blueprints WHERE scope = ?", (self.scope,)
                )
                return cursor.rowcount

    def prune(
        self,
        *,
        keep_unused: bool = False,
        min_times_placed: int | None = None,
        keep_newest: int | None = None,
    ) -> list[str]:
        """Trainer-side decay policy. Returns removed names.

        Ranking keeps the most-placed blueprints first, then the newest.
        ``keep_newest`` retains that many top-ranked entries regardless of
        usage; ``min_times_placed`` protects anything used at least that
        many times.
        """

        def _rank(record: BlueprintRecord) -> tuple[int, str]:
            return (-record.times_placed, record.created_at or "")

        with self._lock:
            if not self.persistent:
                records = sorted(self._memory.values(), key=_rank)
            else:
                records = []
                with self._connect() as conn:
                    rows = conn.execute(
                        """
                        SELECT name, content, content_sha256, entity_count,
                               center_x, center_y, created_tick, times_placed,
                               last_used_tick, created_at
                        FROM blueprints WHERE scope = ?
                        """,
                        (self.scope,),
                    ).fetchall()
                for row in rows:
                    records.append(
                        BlueprintRecord(
                            name=row[0],
                            content=row[1],
                            content_sha256=row[2],
                            entity_count=row[3],
                            center_x=row[4],
                            center_y=row[5],
                            created_tick=row[6],
                            times_placed=row[7],
                            last_used_tick=row[8],
                            scope=self.scope,
                        )
                    )
                # SQLite created_at ordering is the age tiebreak.
                records.sort(key=lambda r: _rank(r))

            survivors: set[str] = set()
            if keep_newest is not None:
                survivors.update(
                    record.name for record in records[: max(keep_newest, 0)]
                )
            removed: list[str] = []
            for record in records:
                if record.name in survivors:
                    continue
                if min_times_placed is not None and (
                    record.times_placed >= min_times_placed
                ):
                    continue
                if self.persistent:
                    with self._connect() as conn:
                        conn.execute(
                            "DELETE FROM blueprints WHERE scope = ? AND name = ?",
                            (self.scope, record.name),
                        )
                else:
                    del self._memory[record.name]
                removed.append(record.name)
            return removed


__all__ = [
    "BLUEPRINT_STORE_VERSION",
    "MAX_BLUEPRINT_BYTES",
    "DEFAULT_MAX_PER_SCOPE",
    "BlueprintStore",
    "BlueprintRecord",
    "BlueprintError",
    "BlueprintQuotaExceeded",
    "BlueprintNotFound",
    "BlueprintInvalid",
    "default_db_path",
]
