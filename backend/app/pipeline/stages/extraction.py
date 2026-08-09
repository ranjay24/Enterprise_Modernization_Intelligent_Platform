"""Extraction stage — downloads and extracts ZIP from S3."""

from __future__ import annotations

import json
import os
import tempfile
import zipfile

import structlog

from app.artifacts.models import Artifact, ArtifactMetadata
from app.artifacts.version import ArtifactVersioner
from app.aws.s3 import S3Repository
from app.pipeline.context import PipelineContext
from app.pipeline.stage import PipelineStage
from app.utils.zip_utils import ZipSafetyError, _safe_member_path, validate_zip_safety

logger = structlog.get_logger(__name__)


class ExtractionStage(PipelineStage):
    """Extracts the uploaded ZIP file from S3 into a temporary directory."""

    name = "extraction"
    phase = "extracting"
    generator = "sprint4-pipeline"
    depends_on: list[str] = []

    def validate_prerequisites(self, context: PipelineContext) -> list[str]:
        if not context.job_id:
            return ["job_id is required"]
        return []

    def execute(self, context: PipelineContext) -> Artifact:
        s3_repo = S3Repository()
        job_id = context.job_id
        tmp_zip = None
        extract_dir = None

        try:
            # Find ZIP in S3
            paginator = s3_repo.client.get_paginator("list_objects_v2")
            zip_key = None
            for page in paginator.paginate(Bucket=s3_repo.bucket, Prefix=f"jobs/{job_id}/raw/"):
                for obj in page.get("Contents", []):
                    if obj["Key"].endswith(".zip"):
                        zip_key = obj["Key"]
                        break
                if zip_key:
                    break

            if not zip_key:
                raise ValueError(f"No ZIP file found for job {job_id}")

            # Download ZIP
            fd, tmp_zip = tempfile.mkstemp(suffix=".zip")
            os.close(fd)
            try:
                s3_repo.client.download_file(s3_repo.bucket, zip_key, tmp_zip)

                # Capture file size BEFORE extraction and deletion
                zip_size_bytes = os.path.getsize(tmp_zip)

                # Extract
                extract_dir = tempfile.mkdtemp()
                with zipfile.ZipFile(tmp_zip, "r") as zf:
                    validate_zip_safety(zf)
                    for member in zf.infolist():
                        _safe_member_path(extract_dir, member.filename)
                        zf.extract(member, extract_dir)
            except ZipSafetyError as exc:
                raise ValueError(f"Unsafe ZIP archive: {exc}")

            content = {
                "extracted_path": extract_dir,
                "zip_key": zip_key,
                "zip_size_bytes": zip_size_bytes,
            }

            logger.info("extraction_complete", job_id=job_id, path=extract_dir, zip_size=zip_size_bytes)

            versioner = ArtifactVersioner()
            return Artifact(
                metadata=ArtifactMetadata(
                    artifact_id=versioner.generate_artifact_id(),
                    artifact_type=self.name,
                    job_id=job_id,
                    generator=self.generator,
                    platform_version=versioner.get_platform_version(),
                    checksum=versioner.compute_checksum(content),
                    size_bytes=len(json.dumps(content)),
                ),
                content=content,
            )

        finally:
            # Always clean up temporary ZIP file
            if tmp_zip and os.path.exists(tmp_zip):
                try:
                    os.remove(tmp_zip)
                except OSError:
                    pass
