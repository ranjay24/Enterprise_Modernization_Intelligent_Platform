"""Report worker — generates and stores analysis reports using shared builders."""

from __future__ import annotations

import structlog

from app.artifacts.repository import ArtifactRepository
from app.reports.builders import build_all_reports
from app.services import events

logger = structlog.get_logger(__name__)


def handle_report_job(job_id: str, report_type: str = "full") -> dict:
    """Generate reports for a completed analysis job."""
    artifact_repo = ArtifactRepository()

    try:
        # Load the results assembly artifact
        results = artifact_repo.load_content(job_id, "results_assembly")
        if not results:
            logger.warning("no_results_found", job_id=job_id)
            return {"error": "No results found for job"}

        # Generate all reports using shared builders
        reports = build_all_reports(results)

        # Save each report as an artifact
        for report_name, report_data in reports.items():
            artifact = artifact_repo.create_artifact(
                job_id=job_id,
                stage_name=report_name,
                content=report_data,
                generator="sprint4-report-worker",
            )
            artifact_repo.save(job_id, report_name, artifact)
            events.publish_report_generated(job_id, report_name, f"jobs/{job_id}/artifacts/{report_name}.json")

        logger.info("reports_generated", job_id=job_id, report_count=len(reports))
        return {"reports": list(reports.keys()), "job_id": job_id}

    except Exception as exc:
        logger.error("report_generation_failed", job_id=job_id, error=str(exc))
        raise
