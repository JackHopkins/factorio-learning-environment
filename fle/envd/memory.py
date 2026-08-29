"""Small revisioned notebook used by model-facing evaluation tools.

The store deliberately lives behind envd.  It is not a Python namespace
object and it never exposes a host path to the model.  A lease owns one store,
which makes it survive the short-lived MCP subprocesses OpenCode starts for
individual customer epochs.
"""

from __future__ import annotations

import hashlib
import re
import threading
import uuid
from datetime import datetime, timezone
from typing import Iterable

from fle.envd.errors import (
    MemoryConflict,
    MemoryLimitExceeded,
    MemoryNotFound,
)
from fle.envd.models import (
    MemoryEntry,
    MemoryListResponse,
    MemoryMutation,
    MemoryMutationResponse,
    MemorySearchHit,
    MemorySearchResponse,
    MemoryTraceResponse,
)

MAX_MEMORY_ENTRIES = 512
MAX_MEMORY_KEY_BYTES = 256
MAX_MEMORY_CONTENT_BYTES = 128 * 1024
MAX_MEMORY_TOTAL_BYTES = 2 * 1024 * 1024


class MemoryError(RuntimeError):
    """Base for model-memory validation and optimistic-concurrency errors."""


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _tokens(value: str) -> set[str]:
    return {item for item in re.findall(r"[a-z0-9][a-z0-9_-]*", value.lower()) if item}


def _cursor(cursor: str | int | None) -> int:
    if cursor in (None, ""):
        return 0
    try:
        value = int(cursor)
    except (TypeError, ValueError):
        raise ValueError("cursor must be a non-negative integer") from None
    if value < 0:
        raise ValueError("cursor must be a non-negative integer")
    return value


class SessionMemory:
    """Thread-safe per-lease key/value notebook with an auditable journal."""

    def __init__(
        self,
        *,
        max_entries: int = MAX_MEMORY_ENTRIES,
        max_content_bytes: int = MAX_MEMORY_CONTENT_BYTES,
        max_total_bytes: int = MAX_MEMORY_TOTAL_BYTES,
    ) -> None:
        if min(max_entries, max_content_bytes, max_total_bytes) < 1:
            raise ValueError("memory limits must be positive")
        self.max_entries = max_entries
        self.max_content_bytes = max_content_bytes
        self.max_total_bytes = max_total_bytes
        self._entries: dict[str, MemoryEntry] = {}
        self._revisions: dict[str, int] = {}
        self._mutations: list[MemoryMutation] = []
        self._lock = threading.RLock()

    @staticmethod
    def _validate_key(key: str) -> str:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("memory key must be a non-empty string")
        normalized = key.strip()
        if len(normalized.encode("utf-8")) > MAX_MEMORY_KEY_BYTES:
            raise ValueError(f"memory key exceeds {MAX_MEMORY_KEY_BYTES} bytes")
        if normalized.startswith("/") or "\\" in normalized or ".." in normalized.split("/"):
            raise ValueError("memory key must be a relative namespaced key")
        if any(ord(char) < 0x20 for char in normalized):
            raise ValueError("memory key contains a control character")
        return normalized

    def list(self, *, prefix: str = "", limit: int = 50, cursor: str | int | None = None) -> MemoryListResponse:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        start = _cursor(cursor)
        with self._lock:
            keys = sorted(key for key in self._entries if key.startswith(prefix or ""))
            page_keys = keys[start : start + limit]
            entries = [self._entries[key].model_copy(deep=True) for key in page_keys]
            next_cursor = str(start + limit) if start + limit < len(keys) else None
            return MemoryListResponse(
                entries=entries,
                next_cursor=next_cursor,
                total=len(keys),
                retained_bytes=sum(entry.byte_size for entry in self._entries.values()),
            )

    def read(self, key: str) -> MemoryEntry:
        normalized = self._validate_key(key)
        with self._lock:
            entry = self._entries.get(normalized)
            if entry is None:
                raise MemoryNotFound(f"memory key not found: {normalized}")
            return entry.model_copy(deep=True)

    def write(
        self,
        key: str,
        content: str,
        *,
        expected_revision: int | None = None,
    ) -> MemoryMutationResponse:
        normalized = self._validate_key(key)
        if not isinstance(content, str):
            raise ValueError("memory content must be a string")
        content_bytes = len(content.encode("utf-8"))
        if content_bytes > self.max_content_bytes:
            raise ValueError(f"memory content exceeds {self.max_content_bytes} bytes")
        if expected_revision is not None and expected_revision < 0:
            raise ValueError("expected_revision must be non-negative")
        now = datetime.now(timezone.utc)
        digest = _sha256(content)
        with self._lock:
            current = self._entries.get(normalized)
            current_revision = current.revision if current else self._revisions.get(normalized, 0)
            if expected_revision is not None and expected_revision != current_revision:
                raise MemoryConflict(
                    f"memory key {normalized!r} is revision {current_revision}, "
                    f"expected {expected_revision}"
                )
            if current is None and len(self._entries) >= self.max_entries:
                raise MemoryLimitExceeded(f"memory entry limit ({self.max_entries}) reached")
            retained = sum(entry.byte_size for entry in self._entries.values())
            if current is not None:
                retained -= current.byte_size
            if retained + content_bytes > self.max_total_bytes:
                raise MemoryLimitExceeded(f"memory byte limit ({self.max_total_bytes}) reached")
            revision = current_revision + 1
            entry = MemoryEntry(
                key=normalized,
                content=content,
                revision=revision,
                content_sha256=digest,
                byte_size=content_bytes,
                created_at=current.created_at if current else now,
                updated_at=now,
            )
            self._entries[normalized] = entry
            self._revisions[normalized] = revision
            mutation = self._mutation(
                operation="write",
                key=normalized,
                revision=revision,
                content_sha256=digest,
                byte_size=content_bytes,
                expected_revision=expected_revision,
                occurred_at=now,
            )
            return MemoryMutationResponse(entry=entry.model_copy(deep=True), mutation=mutation)

    def delete(
        self,
        key: str,
        *,
        expected_revision: int | None = None,
    ) -> MemoryMutationResponse:
        normalized = self._validate_key(key)
        if expected_revision is not None and expected_revision < 0:
            raise ValueError("expected_revision must be non-negative")
        now = datetime.now(timezone.utc)
        with self._lock:
            current = self._entries.get(normalized)
            current_revision = current.revision if current else self._revisions.get(normalized, 0)
            if current is None:
                raise MemoryNotFound(f"memory key not found: {normalized}")
            if expected_revision is not None and expected_revision != current_revision:
                raise MemoryConflict(
                    f"memory key {normalized!r} is revision {current_revision}, "
                    f"expected {expected_revision}"
                )
            revision = current_revision + 1
            self._entries.pop(normalized, None)
            self._revisions[normalized] = revision
            mutation = self._mutation(
                operation="delete",
                key=normalized,
                revision=revision,
                content_sha256=current.content_sha256,
                byte_size=current.byte_size,
                expected_revision=expected_revision,
                occurred_at=now,
            )
            return MemoryMutationResponse(entry=None, mutation=mutation)

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        cursor: str | int | None = None,
    ) -> MemorySearchResponse:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("memory search query must be non-empty")
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        wanted = _tokens(query)
        with self._lock:
            hits: list[MemorySearchHit] = []
            for entry in self._entries.values():
                searchable = _tokens(f"{entry.key} {entry.content}")
                if not wanted.issubset(searchable):
                    continue
                lower = entry.content.lower()
                token = next(iter(wanted), "")
                position = lower.find(token)
                if position < 0:
                    snippet = entry.content[:240]
                else:
                    start = max(position - 80, 0)
                    snippet = entry.content[start : start + 240]
                hits.append(
                    MemorySearchHit(
                        key=entry.key,
                        revision=entry.revision,
                        content_sha256=entry.content_sha256,
                        snippet=snippet,
                    )
                )
            hits.sort(key=lambda hit: hit.key)
            start = _cursor(cursor)
            page = hits[start : start + limit]
            next_cursor = str(start + limit) if start + limit < len(hits) else None
            return MemorySearchResponse(results=page, next_cursor=next_cursor, total=len(hits))

    def trace(self, *, limit: int = 100, cursor: str | int | None = None) -> MemoryTraceResponse:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        with self._lock:
            start = _cursor(cursor)
            events = [event.model_copy(deep=True) for event in self._mutations[start : start + limit]]
            next_cursor = str(start + limit) if start + limit < len(self._mutations) else None
            return MemoryTraceResponse(events=events, next_cursor=next_cursor, total=len(self._mutations))

    def _mutation(
        self,
        *,
        operation: str,
        key: str,
        revision: int,
        content_sha256: str,
        byte_size: int,
        expected_revision: int | None,
        occurred_at: datetime,
    ) -> MemoryMutation:
        mutation = MemoryMutation(
            mutation_id=f"memory-{uuid.uuid4().hex}",
            operation=operation,
            key=key,
            revision=revision,
            content_sha256=content_sha256,
            byte_size=byte_size,
            expected_revision=expected_revision,
            occurred_at=occurred_at,
        )
        self._mutations.append(mutation)
        return mutation


__all__ = [
    "MAX_MEMORY_CONTENT_BYTES",
    "MAX_MEMORY_ENTRIES",
    "MAX_MEMORY_TOTAL_BYTES",
    "MemoryConflict",
    "MemoryError",
    "MemoryNotFound",
    "SessionMemory",
]
