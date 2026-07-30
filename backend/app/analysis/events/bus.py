"""Lightweight in-process event bus for analysis pipeline events."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    PROJECT_SCANNED = "project.scanned"
    PROJECT_PARSED = "project.parsed"
    METRICS_CALCULATED = "metrics.calculated"
    DEPENDENCIES_GENERATED = "dependencies.generated"
    ARCHITECTURE_DETECTED = "architecture.detected"
    RISKS_DETECTED = "risks.detected"
    READINESS_CALCULATED = "readiness.calculated"
    RECOMMENDATIONS_GENERATED = "recommendations.generated"
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_COMPLETED = "analysis.completed"
    ANALYSIS_FAILED = "analysis.failed"
    ANALYZER_STARTED = "analyzer.started"
    ANALYZER_COMPLETED = "analyzer.completed"
    ANALYZER_FAILED = "analyzer.failed"


@dataclass
class Event:
    event_type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = ""


class EventBus:
    """In-process pub/sub event bus. Grows to EventBridge later."""

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[Callable[[Event], None]]] = {}
        self._history: list[Event] = []

    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def publish(self, event: Event) -> None:
        self._history.append(event)
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass

    def emit(
        self,
        event_type: EventType,
        source: str = "",
        data: dict[str, Any] | None = None,
    ) -> None:
        self.publish(Event(event_type=event_type, data=data or {}, source=source))

    @property
    def history(self) -> list[Event]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()
