"""Worker Lambda entry point — triggered by SQS."""

from __future__ import annotations

import json

import structlog

logger = structlog.get_logger(__name__)


def handler(event, context):
    """SQS-triggered Lambda handler for analysis and report jobs."""
    results = []
    failed = False

    for record in event.get("Records", []):
        try:
            body = json.loads(record.get("body", "{}"))
            job_id = body.get("job_id")
            action = body.get("action", "start_analysis")

            if not job_id:
                logger.error("missing_job_id", record_id=record.get("messageId"))
                failed = True
                results.append({"statusCode": 400, "body": "Missing job_id"})
                continue

            logger.info("worker_received_message", job_id=job_id, action=action)

            if action == "start_analysis":
                from app.services.workers.analysis_worker import handle_analysis_job
                resume_from = body.get("resume_from")
                result = handle_analysis_job(job_id, resume_from=resume_from)
                results.append({"statusCode": 200, "body": result})

            elif action == "generate_report":
                from app.services.workers.report_worker import handle_report_job
                report_type = body.get("report_type", "full")
                result = handle_report_job(job_id, report_type=report_type)
                results.append({"statusCode": 200, "body": result})

            else:
                logger.warning("unknown_action", action=action, job_id=job_id)
                failed = True
                results.append({"statusCode": 400, "body": f"Unknown action: {action}"})

        except Exception as exc:
            failed = True
            logger.error("worker_processing_error", error=str(exc))
            results.append({"statusCode": 500, "body": str(exc)})

    if failed:
        # Returning 200 here would make SQS delete the message and the DLQ
        # redrive (maxReceiveCount: 3) would never fire. Fail the invocation so
        # SQS retries the batch and ultimately redrives it to the DLQ.
        failed_count = sum(1 for r in results if r["statusCode"] >= 400)
        raise RuntimeError(
            f"Worker failed {failed_count} of {len(results)} record(s); "
            "invocation failing so SQS can retry and redrive to the DLQ."
        )

    return {
        "statusCode": 200,
        "body": {
            "processed": len(results),
            "results": results,
        },
    }
