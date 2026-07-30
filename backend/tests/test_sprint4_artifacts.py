"""Sprint 4 tests — Artifact models, repository, versioner."""

import json
from unittest.mock import MagicMock, patch

# ─── Artifact Models ───

class TestArtifactMetadata:
    def test_defaults(self):
        from app.artifacts.models import ArtifactMetadata
        m = ArtifactMetadata()
        assert m.artifact_version == "1.0.0"
        assert m.is_degraded is False
        assert m.generator == ""
        assert m.parent_artifact_ids == []

    def test_to_dict(self):
        from app.artifacts.models import ArtifactMetadata
        m = ArtifactMetadata(artifact_type="static_analysis", generator="test", model_id="nova-pro")
        d = m.to_dict()
        assert d["artifact_type"] == "static_analysis"
        assert d["artifact_version"] == "1.0.0"
        assert "generated_at" in d
        assert d["is_degraded"] is False
        assert d["model_id"] == "nova-pro"

    def test_from_dict_roundtrip(self):
        from app.artifacts.models import ArtifactMetadata
        m = ArtifactMetadata(artifact_type="ai_boundaries", artifact_id="art-1", generator="stage1")
        d = m.to_dict()
        m2 = ArtifactMetadata.from_dict(d)
        assert m2.artifact_type == "ai_boundaries"
        assert m2.artifact_id == "art-1"
        assert m2.generator == "stage1"

    def test_from_dict_minimal(self):
        from app.artifacts.models import ArtifactMetadata
        m = ArtifactMetadata.from_dict({})
        assert m.artifact_type == ""
        assert m.artifact_version == "1.0.0"


class TestArtifact:
    def test_defaults(self):
        from app.artifacts.models import Artifact
        a = Artifact()
        assert a.content == {}
        assert a.metadata.artifact_type == ""

    def test_to_dict(self):
        from app.artifacts.models import Artifact, ArtifactMetadata
        a = Artifact(
            metadata=ArtifactMetadata(artifact_type="static_analysis", artifact_id="art-1"),
            content={"classes": 10},
        )
        d = a.to_dict()
        assert d["content"]["classes"] == 10
        assert d["metadata"]["artifact_type"] == "static_analysis"
        assert d["metadata"]["artifact_id"] == "art-1"

    def test_from_dict(self):
        from app.artifacts.models import Artifact
        data = {
            "metadata": {"artifact_type": "ai_boundaries", "artifact_id": "art-2"},
            "content": {"services": []},
        }
        a = Artifact.from_dict(data)
        assert a.metadata.artifact_id == "art-2"
        assert a.content["services"] == []


class TestArtifactManifest:
    def test_defaults(self):
        from app.artifacts.models import ArtifactManifest
        m = ArtifactManifest()
        assert m.job_id == ""
        assert m.artifacts == []
        assert m.reports == []

    def test_to_dict(self):
        from app.artifacts.models import ArtifactManifest
        m = ArtifactManifest(job_id="job-001", project_name="test-proj")
        d = m.to_dict()
        assert d["job_id"] == "job-001"
        assert d["project_name"] == "test-proj"
        assert "started_at" in d
        assert d["artifacts"] == []
        assert d["reports"] == []

    def test_from_dict(self):
        from app.artifacts.models import ArtifactManifest
        data = {"job_id": "job-002", "total_duration_ms": 5000.0, "checksum": "abc123"}
        m = ArtifactManifest.from_dict(data)
        assert m.job_id == "job-002"
        assert m.total_duration_ms == 5000.0
        assert m.checksum == "abc123"

    def test_from_dict_with_artifacts(self):
        from app.artifacts.models import ArtifactManifest
        data = {
            "job_id": "job-003",
            "artifacts": [{"artifact_id": "a1", "artifact_type": "static_analysis"}],
            "reports": [{"artifact_id": "r1", "artifact_type": "executive_summary"}],
        }
        m = ArtifactManifest.from_dict(data)
        assert len(m.artifacts) == 1
        assert m.artifacts[0].artifact_id == "a1"
        assert len(m.reports) == 1
        assert m.reports[0].artifact_id == "r1"


# ─── Artifact Versioner ───

class TestArtifactVersioner:
    def test_compute_checksum(self):
        from app.artifacts.version import ArtifactVersioner
        c1 = ArtifactVersioner.compute_checksum({"foo": "bar"})
        c2 = ArtifactVersioner.compute_checksum({"foo": "bar"})
        assert c1 == c2
        assert c1.startswith("sha256:")
        assert len(c1) == 71  # "sha256:" + 64 hex chars

    def test_checksum_different_data(self):
        from app.artifacts.version import ArtifactVersioner
        c1 = ArtifactVersioner.compute_checksum({"foo": "bar"})
        c2 = ArtifactVersioner.compute_checksum({"foo": "baz"})
        assert c1 != c2

    def test_checksum_string(self):
        from app.artifacts.version import ArtifactVersioner
        c = ArtifactVersioner.compute_checksum("hello")
        assert c.startswith("sha256:")

    def test_generate_artifact_id(self):
        from app.artifacts.version import ArtifactVersioner
        id1 = ArtifactVersioner.generate_artifact_id()
        id2 = ArtifactVersioner.generate_artifact_id()
        assert id1 != id2
        assert len(id1) == 36  # UUID format

    def test_get_platform_version(self):
        from app.artifacts.version import ArtifactVersioner
        assert ArtifactVersioner.get_platform_version() == "1.0.0"

    def test_get_artifact_version(self):
        from app.artifacts.version import ArtifactVersioner
        assert ArtifactVersioner.get_artifact_version() == "1.0.0"

    def test_now_iso(self):
        from app.artifacts.version import ArtifactVersioner
        ts = ArtifactVersioner.now_iso()
        assert "T" in ts
        assert "Z" in ts or "+" in ts


# ─── Artifact Repository ───

class TestArtifactRepository:
    def test_save_and_load(self):
        from app.artifacts.models import Artifact, ArtifactMetadata
        from app.artifacts.repository import ArtifactRepository
        with patch("app.artifacts.repository.S3Repository") as MockS3:
            mock_s3 = MagicMock()
            MockS3.return_value = mock_s3
            # Make load work
            mock_s3.get_object.side_effect = [
                {"Body": MagicMock(read=lambda: json.dumps({"classes": 5}).encode())},
                {"Body": MagicMock(read=lambda: json.dumps({"artifact_type": "sa", "artifact_id": "a1"}).encode())},
            ]
            repo = ArtifactRepository()
            artifact = Artifact(
                metadata=ArtifactMetadata(artifact_type="static_analysis", artifact_id="a1"),
                content={"classes": 5},
            )
            key = repo.save("job-001", "static_analysis", artifact)
            assert "jobs/job-001/artifacts/static_analysis.json" in key
            assert mock_s3.put_object.call_count == 2

    def test_load_nonexistent_returns_none(self):
        from app.artifacts.repository import ArtifactRepository
        with patch("app.artifacts.repository.S3Repository") as MockS3:
            mock_s3 = MagicMock()
            mock_s3.get_object.side_effect = Exception("NoSuchKey")
            MockS3.return_value = mock_s3
            repo = ArtifactRepository()
            assert repo.load("job-999", "nonexistent") is None

    def test_load_content(self):
        from app.artifacts.repository import ArtifactRepository
        with patch("app.artifacts.repository.S3Repository") as MockS3:
            mock_s3 = MagicMock()
            mock_s3.get_object.return_value = {"Body": MagicMock(read=lambda: json.dumps({"k": "v"}).encode())}
            MockS3.return_value = mock_s3
            repo = ArtifactRepository()
            content = repo.load_content("job-001", "stage_a")
            assert content == {"k": "v"}

    def test_load_content_nonexistent(self):
        from app.artifacts.repository import ArtifactRepository
        with patch("app.artifacts.repository.S3Repository") as MockS3:
            mock_s3 = MagicMock()
            mock_s3.get_object.side_effect = Exception("NoSuchKey")
            MockS3.return_value = mock_s3
            repo = ArtifactRepository()
            assert repo.load_content("job-999", "nonexistent") is None

    def test_save_manifest(self):
        from app.artifacts.models import ArtifactManifest
        from app.artifacts.repository import ArtifactRepository
        with patch("app.artifacts.repository.S3Repository") as MockS3:
            mock_s3 = MagicMock()
            MockS3.return_value = mock_s3
            repo = ArtifactRepository()
            manifest = ArtifactManifest(job_id="job-001")
            key = repo.save_manifest("job-001", manifest)
            assert "manifest.json" in key
            mock_s3.put_object.assert_called_once()

    def test_load_manifest(self):
        from app.artifacts.repository import ArtifactRepository
        with patch("app.artifacts.repository.S3Repository") as MockS3:
            mock_s3 = MagicMock()
            mock_s3.get_object.return_value = {
                "Body": MagicMock(read=lambda: json.dumps({"job_id": "job-001", "project_name": "test"}).encode())
            }
            MockS3.return_value = mock_s3
            repo = ArtifactRepository()
            manifest = repo.load_manifest("job-001")
            assert manifest is not None
            assert manifest.job_id == "job-001"

    def test_create_artifact(self):
        from app.artifacts.repository import ArtifactRepository
        with patch("app.artifacts.repository.S3Repository") as MockS3:
            MockS3.return_value = MagicMock()
            repo = ArtifactRepository()
            artifact = repo.create_artifact(
                job_id="job-001",
                stage_name="test_stage",
                content={"result": "ok"},
                generator="test",
                model_id="nova-pro",
            )
            assert artifact.metadata.artifact_type == "test_stage"
            assert artifact.metadata.job_id == "job-001"
            assert artifact.metadata.generator == "test"
            assert artifact.content["result"] == "ok"
            assert len(artifact.metadata.checksum) > 0
