"""Internal domain model for reports."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ReportDomain:
    """Internal domain representation of a generated report."""
    report_id: str
    job_id: str
    report_type: str
    format: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    content: str = ""
    metadata: dict = field(default_factory=dict)
