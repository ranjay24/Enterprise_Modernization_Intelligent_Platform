"""Worker pool — manages ThreadPoolExecutor lifecycle and collects metrics."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field


@dataclass
class StageTiming:
    """Per-stage execution timing record."""
    stage_name: str
    thread_id: int
    start_time: float
    end_time: float
    queue_wait_ms: float = 0.0

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000

    def to_dict(self) -> dict:
        return {
            "stage_name": self.stage_name,
            "thread_id": self.thread_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": round(self.duration_ms, 2),
            "queue_wait_ms": round(self.queue_wait_ms, 2),
        }


@dataclass
class SchedulerMetrics:
    """Aggregated metrics from parallel pipeline execution."""
    total_stages: int = 0
    layers_executed: int = 0
    max_concurrency: int = 0
    wall_time_ms: float = 0.0
    scheduling_overhead_ms: float = 0.0
    stage_timings: list[StageTiming] = field(default_factory=list)
    contention_events: int = 0
    sequential_mode: bool = False

    @property
    def total_cpu_time_ms(self) -> float:
        return sum(t.duration_ms for t in self.stage_timings)

    @property
    def avg_parallelism(self) -> float:
        if self.wall_time_ms <= 0:
            return 0.0
        return self.total_cpu_time_ms / self.wall_time_ms

    def to_dict(self) -> dict:
        return {
            "total_stages": self.total_stages,
            "layers_executed": self.layers_executed,
            "max_concurrency": self.max_concurrency,
            "wall_time_ms": round(self.wall_time_ms, 2),
            "total_cpu_time_ms": round(self.total_cpu_time_ms, 2),
            "avg_parallelism": round(self.avg_parallelism, 2),
            "scheduling_overhead_ms": round(self.scheduling_overhead_ms, 2),
            "contention_events": self.contention_events,
            "sequential_mode": self.sequential_mode,
            "stage_timings": [t.to_dict() for t in self.stage_timings],
        }


class WorkerPool:
    """Manages a ThreadPoolExecutor and tracks execution metrics.

    Usage::

        pool = WorkerPool(max_workers=4)
        with pool.scope() as executor:
            futures = [executor.submit(fn, arg) for arg in args]
        print(pool.metrics)
    """

    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers
        self._metrics = SchedulerMetrics(max_concurrency=max_workers)
        self._contention_lock = threading.Lock()

    @property
    def metrics(self) -> SchedulerMetrics:
        return self._metrics

    @property
    def max_workers(self) -> int:
        return self._max_workers

    def record_contention(self) -> None:
        with self._contention_lock:
            self._metrics.contention_events += 1

    def record_stage_timing(self, timing: StageTiming) -> None:
        self._metrics.stage_timings.append(timing)

    def create_executor(self) -> ThreadPoolExecutor:
        return ThreadPoolExecutor(max_workers=self._max_workers)

    def reset(self) -> None:
        self._metrics = SchedulerMetrics(max_concurrency=self._max_workers)
