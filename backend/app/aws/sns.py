"""SNS notification client (placeholder for future use)."""

import logging

from app.aws.clients import AWSClients

logger = logging.getLogger(__name__)


class SNSRepository:
    """SNS notification operations."""

    def __init__(self, clients: AWSClients):
        self._clients = clients

    def publish_notification(
        self,
        subject: str,
        message: str,
        topic_arn: Optional[str] = None,
    ) -> Optional[str]:
        try:
            arn = topic_arn or f"arn:aws:sns:{self._clients._settings.aws_region}:{self._clients._settings.aws_account_id}:{self._clients._settings.sns_notification_topic}"
            response = self._clients.sns.publish(
                TopicArn=arn,
                Subject=subject,
                Message=message,
            )
            return response.get("MessageId")
        except Exception as exc:
            logger.warning("Failed to publish SNS notification", extra={"error": str(exc)})
            return None
