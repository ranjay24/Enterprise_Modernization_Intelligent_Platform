"""CloudWatch metrics and logging integration."""

import logging

from app.aws.clients import AWSClients

logger = logging.getLogger(__name__)


class CloudWatchRepository:
    """CloudWatch metrics publisher."""

    def __init__(self, clients: AWSClients):
        self._clients = clients

    def put_metric(
        self,
        namespace: str,
        metric_name: str,
        value: float,
        unit: str = "Count",
        dimensions: dict | None = None,
    ) -> None:
        try:
            metric_data = {
                "MetricName": metric_name,
                "Value": value,
                "Unit": unit,
            }
            if dimensions:
                metric_data["Dimensions"] = [
                    {"Name": k, "Value": v} for k, v in dimensions.items()
                ]
            self._clients.cloudwatch.put_metric_data(
                Namespace=namespace,
                MetricData=[metric_data],
            )
        except Exception as exc:
            logger.warning("Failed to put CloudWatch metric", extra={"error": str(exc)})

    def record_execution_time(self, operation: str, duration_ms: float) -> None:
        self.put_metric(
            namespace="EMIP/Backend",
            metric_name="ExecutionTime",
            value=duration_ms,
            unit="Milliseconds",
            dimensions={"Operation": operation},
        )
