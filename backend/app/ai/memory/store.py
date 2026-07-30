"""AI Memory Store — architecture only, not yet implemented.

Prepares the interface for future conversational memory support.
Sprint 4+ will implement full memory persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.analysis_profile import get_profile_for_settings


@dataclass
class MemoryEntry:
    """A single memory entry — stores AI interaction context."""
    entry_id: str = ""
    job_id: str = ""
    session_id: str = ""
    content: str = ""
    role: str = "system"
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ttl_seconds: int = 3600

    def is_expired(self) -> bool:
        """Check if this entry has expired based on TTL."""
        # Sprint 4: implement actual TTL check
        return False

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "job_id": self.job_id,
            "session_id": self.session_id,
            "content": self.content,
            "role": self.role,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "ttl_seconds": self.ttl_seconds,
        }


class MemoryStore:
    """In-memory store for AI interaction context.

    Architecture preparation — not yet integrated into pipeline.
    Sprint 4 will add DynamoDB-backed persistence.

    Future capabilities:
    - Store conversation history per job/session
    - Retrieve relevant context for follow-up queries
    - TTL-based expiry for stale memories
    - Cross-session memory sharing
    """

    def __init__(self, max_entries: int | None = None):
        if max_entries is None:
            max_entries = get_profile_for_settings().memory_max_entries
        self._max_entries = max_entries
        self._entries: list[MemoryEntry] = []

    def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry."""
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

    def retrieve(self, job_id: str, limit: int = 10) -> list[MemoryEntry]:
        """Retrieve recent memories for a job."""
        job_entries = [e for e in self._entries if e.job_id == job_id and not e.is_expired()]
        return job_entries[-limit:]

    def retrieve_by_session(self, session_id: str, limit: int = 10) -> list[MemoryEntry]:
        """Retrieve memories for a specific session."""
        session_entries = [e for e in self._entries if e.session_id == session_id and not e.is_expired()]
        return session_entries[-limit:]

    def clear(self, job_id: str | None = None):
        """Clear memories, optionally filtered by job."""
        if job_id:
            self._entries = [e for e in self._entries if e.job_id != job_id]
        else:
            self._entries.clear()

    def size(self) -> int:
        return len(self._entries)
