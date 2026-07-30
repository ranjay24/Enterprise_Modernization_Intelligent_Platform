"""AI Memory Summary — summarization of past interactions.

Architecture only — Sprint 4 implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.memory.store import MemoryStore
from app.core.analysis_profile import get_profile_for_settings


@dataclass
class MemorySummary:
    """Summarized version of accumulated analysis context.

    Future: used when memory grows beyond context window limits.
    Provides a compressed view of key findings across sessions.
    """
    job_id: str = ""
    key_findings: list[str] = field(default_factory=list)
    decisions_made: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    total_interactions: int = 0
    summary_text: str = ""

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "key_findings": self.key_findings,
            "decisions_made": self.decisions_made,
            "open_questions": self.open_questions,
            "total_interactions": self.total_interactions,
            "summary_text": self.summary_text,
        }


class MemorySummarizer:
    """Summarizes memory entries for a job.

    Architecture preparation — not yet integrated.
    Sprint 4 will use AI to generate summaries of long conversations.
    """

    def __init__(self, store: MemoryStore):
        self._store = store

    def summarize(self, job_id: str) -> MemorySummary:
        """Generate a summary of all memories for a job."""
        profile = get_profile_for_settings()
        entries = self._store.retrieve(job_id, limit=profile.memory_summary_max_entries)

        return MemorySummary(
            job_id=job_id,
            total_interactions=len(entries),
            summary_text=f"Total interactions for job: {len(entries)}",
        )
