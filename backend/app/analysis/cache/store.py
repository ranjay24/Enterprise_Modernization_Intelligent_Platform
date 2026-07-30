"""In-memory LRU-style cache for analysis artifacts."""

from __future__ import annotations

import hashlib
import json
from typing import Any


class AnalysisCache:
    """Simple keyed cache for intermediate analysis results."""

    def __init__(self, max_entries: int = 64) -> None:
        self._store: dict[str, Any] = {}
        self._max_entries = max_entries
        self._access_order: list[str] = []

    def get(self, key: str) -> Any | None:
        if key in self._store:
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            return self._store[key]
        return None

    def put(self, key: str, value: Any) -> None:
        if key in self._store:
            self._access_order.remove(key)
        elif len(self._store) >= self._max_entries:
            oldest = self._access_order.pop(0)
            del self._store[oldest]
        self._store[key] = value
        self._access_order.append(key)

    def has(self, key: str) -> bool:
        return key in self._store

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)
        if key in self._access_order:
            self._access_order.remove(key)

    def clear(self) -> None:
        self._store.clear()
        self._access_order.clear()

    @property
    def size(self) -> int:
        return len(self._store)

    @staticmethod
    def make_key(*parts: Any) -> str:
        raw = json.dumps(parts, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
