"""Prompt statistics logging — tracks AI calls for observability.

Generates ``prompt_stats.json`` per analysis stage and
``benchmark_summary.json`` for the full run.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class PromptCallRecord:
    stage: str = ""
    prompt_char_count: int = 0
    response_char_count: int = 0
    max_tokens_requested: int = 0
    duration_ms: int = 0
    model_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    success: bool = True


class PromptStatsCollector:
    """Collects prompt statistics across a single analysis run."""

    def __init__(self, job_id: str, output_dir: str | None = None):
        self.job_id = job_id
        self._records: list[PromptCallRecord] = []
        self._start_time = time.monotonic()
        if output_dir:
            self._output_dir = Path(output_dir)
        else:
            cwd = Path.cwd()
            self._output_dir = cwd / "logs" / job_id

    def record_call(
        self,
        stage: str,
        prompt_char_count: int,
        response_char_count: int,
        max_tokens_requested: int,
        model_id: str = "",
        success: bool = True,
    ) -> PromptCallRecord:
        record = PromptCallRecord(
            stage=stage,
            prompt_char_count=prompt_char_count,
            response_char_count=response_char_count,
            max_tokens_requested=max_tokens_requested,
            model_id=model_id,
            success=success,
            duration_ms=int((time.monotonic() - self._start_time) * 1000),
        )
        self._records.append(record)
        return record

    def flush(self) -> dict[str, Any]:
        """Write prompt_stats.json and return summary data."""
        if not self._records:
            return {}

        output_dir = self._output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        stats_path = output_dir / "prompt_stats.json"
        stats_data = {
            "job_id": self.job_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_calls": len(self._records),
            "records": [asdict(r) for r in self._records],
        }
        stats_path.write_text(json.dumps(stats_data, indent=2, default=str))
        logger.info("prompt_stats_written", path=str(stats_path), records=len(self._records))

        total_prompt_chars = sum(r.prompt_char_count for r in self._records)
        total_response_chars = sum(r.response_char_count for r in self._records)
        total_duration_ms = sum(r.duration_ms for r in self._records)
        stage_counts: dict[str, int] = {}
        for r in self._records:
            stage_counts[r.stage] = stage_counts.get(r.stage, 0) + 1

        summary = {
            "job_id": self.job_id,
            "total_prompt_chars": total_prompt_chars,
            "total_response_chars": total_response_chars,
            "total_duration_ms": total_duration_ms,
            "total_calls": len(self._records),
            "stages": stage_counts,
            "records": [asdict(r) for r in self._records],
        }

        benchmark_path = output_dir / "benchmark_summary.json"
        benchmark_path.write_text(json.dumps(summary, indent=2, default=str))
        logger.info("benchmark_summary_written", path=str(benchmark_path))

        return summary

    @property
    def records(self) -> list[PromptCallRecord]:
        return list(self._records)
