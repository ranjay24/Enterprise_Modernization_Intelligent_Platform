"""Schema contract tests — codegen statuses must serialize through JobResponse."""


class TestJobStatusCodegen:
    """JobStatus enum covers every status the codegen pipeline writes."""

    def test_generation_with_warnings_is_valid_status(self):
        from app.models.schemas import JobStatus

        assert JobStatus.GENERATION_WITH_WARNINGS == "generation_with_warnings"

    def test_generation_with_warnings_serializes_through_job_response(self):
        from app.models.schemas import JobResponse

        job = JobResponse(
            job_id="job-123",
            status="generation_with_warnings",
            filename="legacy-app.zip",
            created_at="2026-08-07T00:00:00Z",
            updated_at="2026-08-07T00:05:00Z",
            progress=100,
            current_phase="code_generation",
        )
        serialized = job.model_dump()
        assert serialized["status"] == "generation_with_warnings"
        assert JobResponse.model_validate(serialized).status == "generation_with_warnings"

    def test_all_codegen_statuses_are_valid(self):
        from app.models.schemas import JobStatus

        for value in ("generating", "generation_complete", "generation_with_warnings"):
            assert value in {s.value for s in JobStatus}


class TestAnalysisPhaseAlignment:
    """AnalysisPhase must cover every stage the pipeline worker actually emits."""

    PIPELINE_STAGES = [
        "extraction",
        "static_analysis",
        "enterprise_analysis",
        "ai_boundaries",
        "ai_readiness",
        "ai_adrs",
        "ai_migration",
        "ai_cost",
        "ai_explainability",
        "results_assembly",
        "report_generation",
        "manifest",
    ]

    def test_every_pipeline_stage_is_a_valid_phase(self):
        from app.models.schemas import AnalysisPhase

        valid = {p.value for p in AnalysisPhase}
        for stage in self.PIPELINE_STAGES:
            assert stage in valid, f"pipeline stage '{stage}' missing from AnalysisPhase"

