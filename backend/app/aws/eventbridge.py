"""EventBridge repository — custom event bus operations."""

from __future__ import annotations

import json

import structlog

from app.aws.clients import AWSClients
from app.core.settings import get_settings

logger = structlog.get_logger(__name__)


class EventBridgeRepository:
    """EventBridge operations for pipeline event publishing."""

    def __init__(self):
        settings = get_settings()
        self._clients = AWSClients(settings=settings)
        self._settings = settings
        self._bus_name = getattr(settings, "eventbridge_bus_name", "emip-events")

    def publish_event(
        self,
        source: str,
        detail_type: str,
        detail: dict,
    ) -> str | None:
        """Publish an event to EventBridge. Returns event ID."""
        try:
            response = self._clients.events.put_events(
                Entries=[
                    {
                        "Source": source,
                        "DetailType": detail_type,
                        "Detail": json.dumps(detail, default=str),
                        "EventBusName": self._bus_name,
                    }
                ]
            )
            failed = response.get("FailedEntryCount", 0)
            if failed:
                logger.error("eventbridge_publish_failed", detail_type=detail_type, response=response)
                return None
            event_id = response.get("Entries", [{}])[0].get("EventId")
            logger.info("event_published", source=source, detail_type=detail_type, event_id=event_id)
            return event_id
        except Exception as exc:
            logger.error("eventbridge_error", source=source, detail_type=detail_type, error=str(exc))
            return None

    def publish_pipeline_event(self, event_type: str, job_id: str, data: dict) -> str | None:
        """Publish a pipeline event."""
        return self.publish_event(
            source="emip.pipeline",
            detail_type=event_type,
            detail={"job_id": job_id, **data},
        )

    def publish_report_event(self, event_type: str, job_id: str, data: dict) -> str | None:
        """Publish a report event."""
        return self.publish_event(
            source="emip.reports",
            detail_type=event_type,
            detail={"job_id": job_id, **data},
        )
