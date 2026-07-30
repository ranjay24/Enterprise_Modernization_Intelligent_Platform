"""SQS repository — message queue operations."""

from __future__ import annotations

import json

import structlog

from app.aws.clients import AWSClients
from app.core.settings import get_settings

logger = structlog.get_logger(__name__)


class SQSRepository:
    """SQS operations for analysis job queuing."""

    def __init__(self):
        settings = get_settings()
        self._clients = AWSClients(settings=settings)
        self._settings = settings

    @property
    def _queue_url(self) -> str:
        return self._clients.sqs.get_queue_url(
            QueueName=self._settings.sqs_analysis_queue
        )["QueueUrl"]

    @property
    def _dlq_url(self) -> str:
        return self._clients.sqs.get_queue_url(
            QueueName=self._settings.sqs_analysis_dlq
        )["QueueUrl"]

    def enqueue_analysis(self, job_id: str, message_body: dict) -> str | None:
        """Send an analysis job message to the queue. Returns message ID."""
        try:
            body = {
                "job_id": job_id,
                "action": "start_analysis",
                **message_body,
            }
            kwargs = {
                "QueueUrl": self._queue_url,
                "MessageBody": json.dumps(body, default=str),
            }
            if self._settings.sqs_analysis_queue.endswith(".fifo"):
                kwargs["MessageGroupId"] = job_id
            response = self._clients.sqs.send_message(**kwargs)
            message_id = response.get("MessageId")
            logger.info("analysis_enqueued", job_id=job_id, message_id=message_id)
            return message_id
        except Exception as exc:
            logger.error("enqueue_failed", job_id=job_id, error=str(exc))
            return None

    def enqueue_report(self, job_id: str, report_type: str = "full") -> str | None:
        """Send a report generation message to the queue."""
        try:
            body = {
                "job_id": job_id,
                "action": "generate_report",
                "report_type": report_type,
            }
            response = self._clients.sqs.send_message(
                QueueUrl=self._queue_url,
                MessageBody=json.dumps(body, default=str),
            )
            return response.get("MessageId")
        except Exception as exc:
            logger.error("report_enqueue_failed", job_id=job_id, error=str(exc))
            return None

    def get_queue_attributes(self) -> dict:
        """Get queue depth and other attributes."""
        try:
            response = self._clients.sqs.get_queue_attributes(
                QueueUrl=self._queue_url,
                AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
            )
            return response.get("Attributes", {})
        except Exception:
            return {}

    def get_dlq_attributes(self) -> dict:
        """Get DLQ depth."""
        try:
            response = self._clients.sqs.get_queue_attributes(
                QueueUrl=self._dlq_url,
                AttributeNames=["ApproximateNumberOfMessages"],
            )
            return response.get("Attributes", {})
        except Exception:
            return {}
