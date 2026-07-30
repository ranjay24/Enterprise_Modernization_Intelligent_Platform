"""Checkpoint manager — saves/loads pipeline state for resume capability."""

from __future__ import annotations

import json

import structlog

from app.aws.dynamodb import JobRepository
from app.aws.s3 import S3Repository
from app.pipeline.state import PipelineState

logger = structlog.get_logger(__name__)


class CheckpointManager:
    """Manages pipeline checkpoints for analysis resume capability."""

    def __init__(self):
        self._s3 = S3Repository()
        self._job_repo = JobRepository()

    def save(self, job_id: str, state: PipelineState) -> None:
        """Save pipeline state to S3 and update DynamoDB reference."""
        try:
            # Save full state to S3
            state_json = json.dumps(state.to_dict(), default=str)
            self._s3.put_object(
                key=f"jobs/{job_id}/checkpoints/pipeline-state.json",
                body=state_json,
                content_type="application/json",
            )

            # Update DynamoDB with checkpoint reference
            self._job_repo.update_job(
                job_id=job_id,
                current_phase=state.current_stage,
                progress=state.progress,
            )

            logger.info(
                "checkpoint_saved",
                job_id=job_id,
                stage=state.current_stage,
                progress=state.progress,
            )
        except Exception as exc:
            logger.warning("checkpoint_save_failed", job_id=job_id, error=str(exc))

    def load(self, job_id: str) -> PipelineState | None:
        """Load pipeline state from S3."""
        try:
            obj = self._s3.get_object(key=f"jobs/{job_id}/checkpoints/pipeline-state.json")
            data = json.loads(obj["Body"].read().decode())
            return PipelineState.from_dict(data)
        except Exception:
            return None

    def get_resume_stage(self, job_id: str) -> str | None:
        """Get the stage name to resume from."""
        state = self.load(job_id)
        if state and state.current_stage:
            return state.current_stage
        return None

    def has_checkpoint(self, job_id: str) -> bool:
        """Check if a checkpoint exists for this job."""
        try:
            self._s3.get_object(key=f"jobs/{job_id}/checkpoints/pipeline-state.json")
            return True
        except Exception:
            return False

    def clear_checkpoint(self, job_id: str) -> None:
        """Remove checkpoint (for fresh restart)."""
        try:
            self._s3.client.delete_object(
                Bucket=self._s3.bucket,
                Key=f"jobs/{job_id}/checkpoints/pipeline-state.json",
            )
        except Exception:
            pass
