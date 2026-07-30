"""Artifact repository — manages versioned artifact storage in S3 with transparent compression."""

from __future__ import annotations

import gzip
import json

import structlog

from app.artifacts.models import Artifact, ArtifactManifest, ArtifactMetadata
from app.artifacts.version import ArtifactVersioner
from app.aws.s3 import S3Repository

logger = structlog.get_logger(__name__)

S3_PREFIX = "jobs/{job_id}/artifacts"

# Compress artifacts larger than this threshold
COMPRESS_THRESHOLD_BYTES = 10_240  # 10KB


class ArtifactRepository:
    """Manages artifact storage and retrieval in S3.

    Artifacts above COMPRESS_THRESHOLD_BYTES are transparently gzip-compressed.
    Loading handles both compressed and uncompressed artifacts transparently.
    """

    def __init__(self):
        self._s3 = S3Repository()
        self._versioner = ArtifactVersioner()

    def save(self, job_id: str, stage_name: str, artifact: Artifact) -> str:
        """Save artifact content + metadata to S3. Returns S3 key."""
        prefix = S3_PREFIX.format(job_id=job_id)
        content_key = f"{prefix}/{stage_name}.json"
        meta_key = f"{prefix}/{stage_name}.meta.json"

        content_bytes = json.dumps(artifact.content, default=str).encode("utf-8")

        if len(content_bytes) > COMPRESS_THRESHOLD_BYTES:
            body = gzip.compress(content_bytes)
            content_type = "application/gzip"
        else:
            body = content_bytes
            content_type = "application/json"

        self._s3.put_object(key=content_key, body=body, content_type=content_type)

        self._s3.put_object(
            key=meta_key,
            body=json.dumps(artifact.metadata.to_dict(), default=str),
            content_type="application/json",
        )

        logger.info("artifact_saved", job_id=job_id, stage=stage_name, key=content_key, compressed=len(content_bytes) > COMPRESS_THRESHOLD_BYTES)
        return content_key

    def load(self, job_id: str, stage_name: str) -> Artifact | None:
        """Load artifact content + metadata from S3."""
        prefix = S3_PREFIX.format(job_id=job_id)
        content_key = f"{prefix}/{stage_name}.json"
        meta_key = f"{prefix}/{stage_name}.meta.json"

        try:
            content_obj = self._s3.get_object(key=content_key)
            raw = content_obj["Body"].read()
            content_type = content_obj.get("ContentType", "application/json")
            if content_type == "application/gzip" or raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            content = json.loads(raw.decode("utf-8"))
        except Exception:
            return None

        try:
            meta_obj = self._s3.get_object(key=meta_key)
            metadata = ArtifactMetadata.from_dict(json.loads(meta_obj["Body"].read().decode()))
        except Exception:
            metadata = ArtifactMetadata(artifact_type=stage_name, job_id=job_id)

        return Artifact(metadata=metadata, content=content)

    def load_content(self, job_id: str, stage_name: str) -> dict | None:
        """Load only the content (no metadata) from an artifact."""
        prefix = S3_PREFIX.format(job_id=job_id)
        content_key = f"{prefix}/{stage_name}.json"
        try:
            obj = self._s3.get_object(key=content_key)
            raw = obj["Body"].read()
            content_type = obj.get("ContentType", "application/json")
            if content_type == "application/gzip" or raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return None

    def artifact_exists(self, job_id: str, stage_name: str) -> bool:
        """Check if an artifact already exists."""
        prefix = S3_PREFIX.format(job_id=job_id)
        content_key = f"{prefix}/{stage_name}.json"
        try:
            self._s3.get_object(key=content_key)
            return True
        except Exception:
            return False

    def list_artifacts(self, job_id: str) -> list[ArtifactMetadata]:
        """List all artifact metadata for a job."""
        prefix = S3_PREFIX.format(job_id=job_id)
        artifacts = []
        try:
            paginator = self._s3.client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self._s3.bucket, Prefix=prefix):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key.endswith(".meta.json"):
                        stage_name = key.split("/")[-1].replace(".meta.json", "")
                        meta = self.load_metadata(job_id, stage_name)
                        if meta:
                            artifacts.append(meta)
        except Exception as exc:
            logger.warning("list_artifacts_failed", job_id=job_id, error=str(exc))
        return artifacts

    def load_metadata(self, job_id: str, stage_name: str) -> ArtifactMetadata | None:
        """Load only metadata for an artifact."""
        prefix = S3_PREFIX.format(job_id=job_id)
        meta_key = f"{prefix}/{stage_name}.meta.json"
        try:
            obj = self._s3.get_object(key=meta_key)
            return ArtifactMetadata.from_dict(json.loads(obj["Body"].read().decode()))
        except Exception:
            return None

    def save_manifest(self, job_id: str, manifest: ArtifactManifest) -> str:
        """Save the analysis manifest."""
        key = f"jobs/{job_id}/artifacts/manifest.json"
        manifest_bytes = json.dumps(manifest.to_dict(), default=str).encode("utf-8")

        if len(manifest_bytes) > COMPRESS_THRESHOLD_BYTES:
            body = gzip.compress(manifest_bytes)
            content_type = "application/gzip"
        else:
            body = manifest_bytes
            content_type = "application/json"

        self._s3.put_object(key=key, body=body, content_type=content_type)
        logger.info("manifest_saved", job_id=job_id, artifact_count=len(manifest.artifacts))
        return key

    def load_manifest(self, job_id: str) -> ArtifactManifest | None:
        """Load the analysis manifest."""
        key = f"jobs/{job_id}/artifacts/manifest.json"
        try:
            obj = self._s3.get_object(key=key)
            raw = obj["Body"].read()
            content_type = obj.get("ContentType", "application/json")
            if content_type == "application/gzip" or raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            data = json.loads(raw.decode("utf-8"))
            return ArtifactManifest.from_dict(data)
        except Exception:
            return None

    def create_artifact(
        self,
        job_id: str,
        stage_name: str,
        content: dict,
        generator: str = "",
        model_id: str = "",
        phase_duration_ms: float = 0.0,
        is_degraded: bool = False,
        parent_artifact_ids: list[str] | None = None,
    ) -> Artifact:
        """Create a new Artifact with auto-generated metadata."""
        content_json = json.dumps(content, default=str)
        metadata = ArtifactMetadata(
            artifact_id=self._versioner.generate_artifact_id(),
            artifact_type=stage_name,
            artifact_version=self._versioner.get_artifact_version(),
            job_id=job_id,
            generated_at=self._versioner.now_iso(),
            generator=generator,
            model_id=model_id,
            platform_version=self._versioner.get_platform_version(),
            checksum=self._versioner.compute_checksum(content),
            size_bytes=len(content_json),
            phase_duration_ms=phase_duration_ms,
            is_degraded=is_degraded,
            parent_artifact_ids=parent_artifact_ids or [],
        )
        return Artifact(metadata=metadata, content=content)
