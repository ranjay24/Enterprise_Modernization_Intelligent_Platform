"""Pipeline context — shared mutable state flowing through stages."""

from __future__ import annotations

import copy
import threading
from dataclasses import dataclass, field
from typing import Any

from app.artifacts.models import Artifact
from app.pipeline.state import PipelineState


@dataclass
class PipelineContext:
    """Shared context passed to every pipeline stage.

    Each stage reads from and writes to this context.
    The engine manages the lifecycle.
    Thread-safe: set_result/get_result acquire an internal lock.
    """
    job_id: str = ""
    data: dict = field(default_factory=dict)
    state: PipelineState = field(default_factory=PipelineState)
    results: dict[str, Artifact] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def set_result(self, stage_name: str, artifact: Artifact) -> None:
        """Store a stage's output artifact. Thread-safe."""
        with self._lock:
            self.results[stage_name] = artifact

    def get_result(self, stage_name: str) -> Artifact | None:
        """Get a stage's output artifact. Thread-safe."""
        with self._lock:
            return self.results.get(stage_name)

    def get_result_data(self, stage_name: str) -> dict:
        """Get a deep copy of a stage's content dict. Thread-safe.

        A copy is returned so concurrent stages cannot mutate shared analysis
        data (parallel execution runs independent stages in separate threads).
        """
        with self._lock:
            artifact = self.results.get(stage_name)
            if not artifact:
                return {}
            return copy.deepcopy(artifact.content)

    def get_data(self) -> dict:
        """Get the initial analysis data."""
        return self.data

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "job_id": self.job_id,
                "data_keys": list(self.data.keys()),
                "result_stages": list(self.results.keys()),
                "metadata_keys": list(self.metadata.keys()),
                "state": self.state.to_dict(),
            }
