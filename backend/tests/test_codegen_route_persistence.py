"""P2.4 — codegen progress persists to DynamoDB, not an in-memory dict.

Guards that codegen status (progress + current_stage) survives a backend
restart because every agent milestone is written to the job record via
JobRepository.update_job, and that the status endpoint reads only from the
job record (no _active_generations module state).
"""

import asyncio
import os

import pytest

from app.exceptions.custom import ResourceNotFoundException, ValidationFailedException
from app.routes import codegen as codegen_routes
from app.models.job import JobDomain


def _run(coro):
    return asyncio.run(coro)


class FakeJobRepo:
    def __init__(self):
        self.jobs: dict[str, JobDomain] = {}
        self.updates: list[dict] = []

    def get_job(self, job_id: str):
        return self.jobs.get(job_id)

    def update_job(self, job_id: str, **kwargs):
        job = self.jobs.setdefault(
            job_id,
            JobDomain(job_id=job_id, status="analysis_complete", filename="test.zip"),
        )
        for k, v in kwargs.items():
            setattr(job, k, v)
        self.updates.append({"job_id": job_id, **kwargs})


class FakeArtifactRepo:
    def __init__(self, content: dict | None = None, plan: dict | None = None):
        self.content = content or {}
        self.plan = plan

    def load_content(self, job_id: str, kind: str):
        if kind == "codegen_plan":
            return self.plan
        return self.content.get(kind)

    def artifact_exists(self, job_id: str, kind: str) -> bool:
        return False


@pytest.fixture(autouse=True)
def _fakes(monkeypatch):
    jobs = FakeJobRepo()
    monkeypatch.setattr(codegen_routes, "JobRepository", lambda: jobs)
    monkeypatch.setattr(codegen_routes, "ArtifactRepository", lambda: FakeArtifactRepo())
    return jobs


def test_job_domain_roundtrips_codegen_stage():
    job = JobDomain(job_id="job-p24", status="generating", filename="f.zip")
    job.codegen_stage = "review"
    job.progress = 80
    restored = JobDomain.from_dict(job.to_dict())
    assert restored.codegen_stage == "review"
    assert restored.progress == 80


def test_start_persists_generating_state(monkeypatch):
    started = []
    monkeypatch.setattr(codegen_routes, "_run_codegen_sync", lambda jid: started.append(jid))
    codegen_routes.JobRepository().update_job(job_id="job-p24-1", status="analysis_complete")
    result = _run(codegen_routes.start_code_generation("job-p24-1"))
    assert result["status"] == "started"
    job = codegen_routes.JobRepository().get_job("job-p24-1")
    assert job.status == "generating"
    assert job.progress == 0
    assert job.current_phase == "code_generation"
    assert job.codegen_stage == "starting"


def test_start_rejects_job_not_analysis_complete():
    repo = codegen_routes.JobRepository()
    repo.update_job(job_id="job-p24-2", status="uploaded")
    with pytest.raises(ValidationFailedException):
        _run(codegen_routes.start_code_generation("job-p24-2"))


def test_start_missing_job():
    with pytest.raises(ResourceNotFoundException):
        _run(codegen_routes.start_code_generation("job-does-not-exist"))


def test_lambda_path_explicit_local_only(monkeypatch):
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "emip-api")
    repo = codegen_routes.JobRepository()
    repo.update_job(job_id="job-p24-3", status="analysis_complete")
    with pytest.raises(ValidationFailedException) as exc_info:
        _run(codegen_routes.start_code_generation("job-p24-3"))
    msg = str(exc_info.value)
    assert "local" in msg.lower() and "SQS" in msg


def test_progress_callback_persists_each_milestone():
    codegen_routes._progress_callback("job-p24-4", 15, "service_planning")
    codegen_routes._progress_callback("job-p24-4", 80, "review")
    job = codegen_routes.JobRepository().get_job("job-p24-4")
    assert job.progress == 80
    assert job.codegen_stage == "review"


def test_run_sync_success_persists_complete(monkeypatch):
    monkeypatch.setattr(codegen_routes, "CodeGenOrchestrator", lambda **kw: _FakeOrch(ok=True))
    codegen_routes._run_codegen_sync("job-p24-5")
    job = codegen_routes.JobRepository().get_job("job-p24-5")
    assert job.status == "generation_complete"
    assert job.progress == 100
    assert job.codegen_stage == "finalize"
    assert job.current_phase == "generation_complete"


def test_run_sync_failure_persists_failed(monkeypatch):
    monkeypatch.setattr(codegen_routes, "CodeGenOrchestrator", lambda **kw: _FakeOrch(ok=False))
    codegen_routes._run_codegen_sync("job-p24-6")
    job = codegen_routes.JobRepository().get_job("job-p24-6")
    assert job.status == "failed"
    assert job.codegen_stage == "failed"
    assert "Code generation failed" in job.error


def test_status_reads_persisted_progress_after_restart(monkeypatch):
    repo = codegen_routes.JobRepository()
    repo.update_job(job_id="job-p24-7", status="generating", progress=45, codegen_stage="service_planning")
    result = _run(codegen_routes.codegen_status("job-p24-7"))
    assert result["in_progress"] is True
    assert result["progress"] == 45
    assert result["current_stage"] == "service_planning"


def test_status_complete_job(monkeypatch):
    monkeypatch.setattr(
        codegen_routes,
        "ArtifactRepository",
        lambda: FakeArtifactRepo(content={"codegen_summary": {"status": "generation_complete"}}),
    )
    repo = codegen_routes.JobRepository()
    repo.update_job(job_id="job-p24-8", status="generation_complete", progress=100, codegen_stage="finalize")
    result = _run(codegen_routes.codegen_status("job-p24-8"))
    assert result["in_progress"] is False
    assert result["progress"] == 100
    assert result["current_stage"] == "finalize"
    assert result["summary"]["status"] == "generation_complete"


def test_status_missing_job_no_summary():
    result = _run(codegen_routes.codegen_status("job-p24-missing"))
    assert result["in_progress"] is False
    assert result["progress"] == 0
    assert result["current_stage"] == "idle"


class _FakeOrch:
    def __init__(self, ok: bool, **kwargs):
        self._ok = ok
        self._kwargs = kwargs

    def run(self, job_id: str):
        if not self._ok:
            raise RuntimeError("boom")
