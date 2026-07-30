"""AI Memory Context — prepares context window from stored memories.

Architecture only — Sprint 4 implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.memory.store import MemoryEntry, MemoryStore


def _get_memory_profile():
    from app.core.analysis_profile import get_active_profile
    from app.core.settings import get_settings
    _s = get_settings()
    return get_active_profile(_s.analysis_mode, _s.bedrock_max_tokens, _s.ai_prompt_max_tokens)


@dataclass
class MemoryContext:
    """Prepared context window assembled from memory entries.

    Future: will be used to provide conversational context for follow-up
    queries about the same analysis job.
    """
    job_id: str = ""
    session_id: str = ""
    entries: list[MemoryEntry] = field(default_factory=list)
    total_tokens_estimate: int = 0
    truncated: bool = False

    def to_prompt_context(self, max_tokens: int | None = None) -> str:
        """Convert memory entries into a prompt-compatible context string."""
        if not self.entries:
            return ""

        profile = _get_memory_profile()
        if max_tokens is None:
            max_tokens = profile.memory_max_tokens
        entry_limit = profile.memory_entry_max_chars

        lines = ["PREVIOUS ANALYSIS CONTEXT:"]
        for entry in self.entries:
            lines.append(f"[{entry.role.upper()}] {entry.content[:entry_limit]}")

        context = "\n".join(lines)
        if len(context) > max_tokens * 4:
            context = context[:max_tokens * 4]
            self.truncated = True

        return context


class MemoryContextBuilder:
    """Builds MemoryContext from MemoryStore for a given job.

    Architecture preparation — not yet integrated.
    """

    def __init__(self, store: MemoryStore):
        self._store = store

    def build(self, job_id: str, session_id: str = "", max_entries: int | None = None) -> MemoryContext:
        """Build context from recent memories."""
        if max_entries is None:
            max_entries = _get_memory_profile().memory_max_entries
        entries = self._store.retrieve(job_id, limit=max_entries)

        return MemoryContext(
            job_id=job_id,
            session_id=session_id,
            entries=entries,
            total_tokens_estimate=sum(len(e.content) // 4 for e in entries),
        )
