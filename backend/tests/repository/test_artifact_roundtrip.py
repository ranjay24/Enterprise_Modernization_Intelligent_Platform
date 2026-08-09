"""Artifact repository save→load round-trip tests (P7.6).

Locks that what `save` writes to S3 can be loaded back intact: content,
metadata, is_degraded, schema/artifact version fields, and checksum stability.
Uses an in-memory S3 stub so the round trip exercises the real serialization
code paths end-to-end.
"""

import gzip
from unittest.mock import patch

from app.artifacts.models import Artifact, ArtifactMetadata
from app.artifacts.repository import ArtifactRepository
from app.artifacts.version import ArtifactVersioner


class FakeS3:
    """In-memory S3 stub mirroring boto3 semantics.

    Mirrors S3Repository.put_object behaviour: str bodies are stored as UTF-8
    bytes (boto3 does the same server-side) and get_object always returns
    bytes, so ArtifactRepository.load's `.decode()` works exactly as it does
    against real S3.
    """

    def __init__(self):
        self.store = {}

    def put_object(self, key, body, content_type):
        if isinstance(body, bytes):
            self.store[key] = (body, None)
        else:
            self.store[key] = (body.encode("utf-8"), content_type)

    def get_object(self, key):
        if key not in self.store:
            raise Exception(f"NoSuchKey: {key}")
        body, content_type = self.store[key]
        return {
            "Body": _Readable(body),
            "ContentType": content_type if content_type else "binary/octet-stream",
        }


class _Readable:
    def __init__(self, body):
        self._body = body

    def read(self):
        return self._body


def _repo_with(fake_s3):
    with patch("app.artifacts.repository.S3Repository", return_value=fake_s3):
        return ArtifactRepository()


def _artifact(**overrides):
    content = {"services": [{"name": "Order"}]}
    defaults = dict(
        artifact_id="art-roundtrip-1",
        artifact_type="ai_boundaries",
        job_id="job-rt-1",
        generator="sprint3-ai-layer",
        model_id="amazon.nova-pro-v1:0",
        is_degraded=False,
        checksum=ArtifactVersioner.compute_checksum(content),
    )
    defaults.update(overrides)
    return Artifact(metadata=ArtifactMetadata(**defaults), content=content)


class TestArtifactRoundTrip:
    def test_save_then_load_preserves_content_and_metadata(self):
        fake_s3 = FakeS3()
        repo = _repo_with(fake_s3)

        artifact = _artifact()
        repo.save("job-rt-1", "ai_boundaries", artifact)
        loaded = repo.load("job-rt-1", "ai_boundaries")

        assert loaded is not None
        assert loaded.content == artifact.content
        assert loaded.metadata.artifact_type == "ai_boundaries"
        assert loaded.metadata.job_id == "job-rt-1"
        assert loaded.metadata.generator == "sprint3-ai-layer"
        assert loaded.metadata.model_id == "amazon.nova-pro-v1:0"
        assert loaded.metadata.artifact_id == "art-roundtrip-1"
        assert loaded.metadata.is_degraded is False

    def test_roundtrip_preserves_is_degraded(self):
        fake_s3 = FakeS3()
        repo = _repo_with(fake_s3)

        artifact = _artifact(is_degraded=True, model_id="deterministic-fallback")
        repo.save("job-rt-1", "ai_boundaries", artifact)
        loaded = repo.load("job-rt-1", "ai_boundaries")

        assert loaded.metadata.is_degraded is True
        assert loaded.metadata.model_id == "deterministic-fallback"

    def test_roundtrip_checksum_matches_recomputed(self):
        fake_s3 = FakeS3()
        repo = _repo_with(fake_s3)

        artifact = _artifact()
        repo.save("job-rt-1", "ai_boundaries", artifact)
        loaded = repo.load("job-rt-1", "ai_boundaries")

        assert loaded.metadata.checksum == ArtifactVersioner.compute_checksum(artifact.content)

    def test_roundtrip_preserves_version_fields(self):
        fake_s3 = FakeS3()
        repo = _repo_with(fake_s3)

        artifact = _artifact()
        artifact.metadata.artifact_version = "1.1.0"
        artifact.metadata.platform_version = "2.0.0"
        artifact.metadata.analysis_version = "2.5.0"
        repo.save("job-rt-1", "ai_boundaries", artifact)
        loaded = repo.load("job-rt-1", "ai_boundaries")

        assert loaded.metadata.artifact_version == "1.1.0"
        assert loaded.metadata.platform_version == "2.0.0"
        assert loaded.metadata.analysis_version == "2.5.0"

    def test_large_artifact_gzip_roundtrip(self):
        fake_s3 = FakeS3()
        repo = _repo_with(fake_s3)

        content = {"blobs": ["x" * 5000 for _ in range(5)]}  # far above 10 KB threshold
        artifact = Artifact(metadata=ArtifactMetadata(artifact_type="static_analysis", job_id="job-rt-1"), content=content)
        repo.save("job-rt-1", "static_analysis", artifact)
        loaded = repo.load("job-rt-1", "static_analysis")

        assert loaded.content == content
        content_key = "jobs/job-rt-1/artifacts/static_analysis.json"
        stored_body, stored_type = fake_s3.store[content_key]
        assert stored_type is None  # bytes bodies are stored without a ContentType override
        assert stored_body[:2] == b"\x1f\x8b"  # gzip magic bytes
        assert gzip.decompress(stored_body) == __import__("json").dumps(content, default=str).encode("utf-8")

    def test_load_nonexistent_after_save_other_stage_returns_none(self):
        fake_s3 = FakeS3()
        repo = _repo_with(fake_s3)

        artifact = _artifact()
        repo.save("job-rt-1", "ai_boundaries", artifact)

        assert repo.load("job-rt-1", "never_saved") is None
