"""CodeGen orchestrator — runs the multi-agent code generation loop for a job."""

from __future__ import annotations

import structlog
from collections.abc import Callable
from typing import Any

from app.agents.architecture import ArchitectureDesignerAgent
from app.agents.generator import CodeGenerationAgent
from app.agents.planner import ServicePlannerAgent
from app.agents.reviewer import ReviewAgent
from app.artifacts.repository import ArtifactRepository
from app.artifacts.version import ArtifactVersioner
from app.aws.dynamodb import JobRepository
from app.codegen import models as codegen_models
from app.codegen.project_builder import build_scaffold_service

logger = structlog.get_logger(__name__)

MAX_PLAN_ITERATIONS = 3

STAGE_NAMES = [
    "architecture_design",
    "service_planning",
    "code_generation",
    "review",
    "finalize",
]


class CodeGenOrchestrator:
    """Coordinates the four agents and persists their outputs as artifacts.

    Loop: architecture designer → planner → generator (per service, per wave) →
    reviewer. If the reviewer finds blocking issues, the planner revises with the
    findings and affected services are regenerated (max MAX_PLAN_ITERATIONS).
    """

    def __init__(
        self,
        artifact_repo: ArtifactRepository | None = None,
        progress_callback: Callable[[str, int, str], None] | None = None,
    ):
        self._artifact_repo = artifact_repo or ArtifactRepository()
        self._versioner = ArtifactVersioner()
        self._progress_callback = progress_callback
        self._history: list[dict] = []

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    def _report(self, job_id: str, progress: int, stage: str):
        if self._progress_callback:
            try:
                self._progress_callback(job_id, progress, stage)
            except Exception:
                pass

    def _update_job(self, job_id: str, **kwargs):
        try:
            JobRepository().update_job(job_id=job_id, **kwargs)
        except Exception as exc:
            logger.warning("codegen_job_update_failed", job_id=job_id, error=str(exc))

    # ------------------------------------------------------------------ inputs
    def _load_analysis(self, job_id: str) -> dict:
        """Load assembled results + individual artifacts for the agents."""
        from app.aws.s3 import S3Repository

        analysis: dict = {}

        artifact = self._artifact_repo.load(job_id, "results_assembly")
        if artifact:
            analysis = artifact.content
        else:
            try:
                s3 = S3Repository()
                obj = s3.get_object(key=f"jobs/{job_id}/analysis/results.json")
                analysis = json_loads(obj["Body"].read())
            except Exception as exc:
                logger.warning("codegen_results_load_failed", job_id=job_id, error=str(exc))

        return {
            "assembled": analysis,
            "static_analysis": self._artifact_repo.load_content(job_id, "static_analysis") or {},
            "enterprise_analysis": self._artifact_repo.load_content(job_id, "enterprise_analysis") or {},
            "boundaries": analysis.get("service_boundaries", [])
                or (self._artifact_repo.load_content(job_id, "ai_boundaries") or {}).get("services", []),
            "migration_waves": analysis.get("migration_waves")
                or (self._artifact_repo.load_content(job_id, "ai_migration") or {}),
            "cost": analysis.get("cost_comparison")
                or (self._artifact_repo.load_content(job_id, "ai_cost") or {}),
        }

    # ------------------------------------------------------------------ agents
    def _design_architecture(self, job_id: str, ctx: dict) -> dict:
        agent = ArchitectureDesignerAgent()
        self._report(job_id, 5, "architecture_design")
        design, metadata, _ = agent.run(
            analysis_data=ctx["static_analysis"],
            boundaries=ctx["boundaries"],
            waves=ctx["migration_waves"],
            cost=ctx["cost"],
            job_id=job_id,
        )
        self._save_artifact(job_id, agent.output_artifact, design, agent.name, metadata)
        self._history.append({"agent": agent.agent_id, "status": "completed", "metadata": metadata})
        return design

    def _plan(self, job_id: str, ctx: dict, architecture: dict, feedback: list[dict] | None) -> dict:
        agent = ServicePlannerAgent()
        self._report(job_id, 15, "service_planning")
        plan, metadata, _ = agent.run(
            architecture=architecture,
            boundaries=ctx["boundaries"],
            analysis_data=ctx["static_analysis"],
            review_feedback=feedback,
            job_id=job_id,
        )
        self._save_artifact(job_id, agent.output_artifact, plan, agent.name, metadata)
        self._history.append({"agent": agent.agent_id, "status": "completed", "metadata": metadata})
        return plan

    def _generate_service(
        self,
        job_id: str,
        ctx: dict,
        service_plan: dict,
        regeneration_context: dict | None = None,
        progress: int = 0,
    ) -> dict:
        agent = CodeGenerationAgent()
        service_id = codegen_models.normalize_service_id(service_plan, "service")
        self._report(job_id, progress, f"code_generation_{service_id}")

        source_boundary = self._boundary_for(ctx, service_plan)
        code, metadata, _ = agent.run(
            service_plan=service_plan,
            source_boundary=source_boundary,
            analysis_data=ctx["static_analysis"],
            regeneration_context=regeneration_context,
            job_id=job_id,
        )
        code = codegen_models.normalize_service_code(code)
        code["service_id"] = service_id
        self._save_artifact(job_id, f"service_code_{service_id}", code, agent.name, metadata)
        self._history.append({"agent": agent.agent_id, "service": service_id, "status": "completed", "metadata": metadata})
        return code

    def _review(self, job_id: str, ctx: dict, codes: list[dict], plan: dict, architecture: dict, iteration: int) -> dict:
        agent = ReviewAgent()
        self._report(job_id, 80, "review")
        report, metadata, _ = agent.run(
            services_code=codes,
            plan=plan,
            architecture=architecture,
            iteration=iteration,
            job_id=job_id,
        )
        self._save_artifact(job_id, agent.output_artifact, report, agent.name, metadata)
        self._history.append({"agent": agent.agent_id, "iteration": iteration, "status": "completed", "metadata": metadata})
        return report

    # --------------------------------------------------------------- helpers
    def _boundary_for(self, ctx: dict, service_plan: dict) -> dict:
        source_boundary = service_plan.get("source_boundary")
        for b in ctx["boundaries"]:
            if b.get("name") == source_boundary or b.get("name") == service_plan.get("id"):
                return b
        return {"name": service_plan.get("id", "service"), "classes": service_plan.get("source_classes", [])}

    def _save_artifact(self, job_id: str, stage_name: str, content: dict, generator: str, metadata: dict):
        model_id = metadata.get("model_id", "")
        is_degraded = bool(metadata.get("used_fallback") or metadata.get("error"))
        artifact = self._artifact_repo.create_artifact(
            job_id=job_id,
            stage_name=stage_name,
            content=content,
            generator=generator,
            model_id=model_id,
            is_degraded=is_degraded,
        )
        self._artifact_repo.save(job_id, stage_name, artifact)

    def _ordered_services(self, plan: dict) -> list[dict]:
        """Return service plans ordered by waves (dependency-safe)."""
        by_id: dict[str, dict] = {}
        for svc in codegen_models.normalize_service_list(plan):
            sid = codegen_models.normalize_service_id(svc)
            if sid:
                by_id[sid] = svc

        ordered: list[dict] = []
        seen: set[str] = set()
        waves = sorted(codegen_models.normalize_waves(plan), key=lambda w: int(w.get("wave", 99)))
        for wave in waves:
            for sid in wave.get("services", []) or []:
                sid = str(sid)
                if sid in by_id and sid not in seen:
                    ordered.append(by_id[sid])
                    seen.add(sid)
        for sid, svc in by_id.items():
            if sid not in seen:
                ordered.append(svc)
                seen.add(sid)
        return ordered

    def _affected_service_ids(self, findings: list[dict], plan: dict) -> set[str]:
        """Map findings to affected services using the plan's file/package info."""
        affected: set[str] = set()
        for svc in codegen_models.normalize_service_list(plan):
            sid = codegen_models.normalize_service_id(svc)
            package = str(svc.get("package", ""))
            for f in findings:
                file = str(f.get("file", ""))
                if (package and package in file) or sid in file:
                    affected.add(sid)
        return affected

    # ------------------------------------------------------------------ run
    def run(self, job_id: str, max_iterations: int = MAX_PLAN_ITERATIONS) -> dict:
        """Execute the full code generation loop for a job. Returns a summary dict."""
        ctx = self._load_analysis(job_id)
        if not ctx["boundaries"]:
            raise ValueError("No service boundaries available — run the analysis pipeline first")

        self._update_job(job_id, status="generating", current_phase="code_generation", progress=10)

        architecture = self._design_architecture(job_id, ctx)
        plan = self._plan(job_id, ctx, architecture, None)

        services_codes: dict[str, dict] = {}
        report: dict | None = None
        iteration = 0

        for iteration in range(1, max_iterations + 1):
            self._report(job_id, 30 + (iteration - 1) * 20, "code_generation")
            ordered = self._ordered_services(plan)
            total = max(len(ordered), 1)
            for idx, service_plan in enumerate(ordered):
                sid = codegen_models.normalize_service_id(service_plan, "service")
                regeneration = None
                if report:
                    findings = [f for f in codegen_models.blocking_findings(report) if sid in str(f.get("file", ""))]
                    if findings:
                        regeneration = {"findings": findings, "iteration": iteration - 1}
                svc_progress = min(74, 30 + round(40 * (idx + 1) / total))
                services_codes[sid] = self._generate_service(
                    job_id, ctx, service_plan,
                    regeneration_context=regeneration,
                    progress=svc_progress,
                )

            self._report(job_id, 80, "review")
            report = self._review(
                job_id, ctx, list(services_codes.values()), plan, architecture, iteration
            )

            if codegen_models.is_approved(report):
                logger.info("codegen_approved", job_id=job_id, iteration=iteration)
                break

            findings = codegen_models.blocking_findings(report)
            if iteration >= max_iterations:
                logger.warning("codegen_max_iterations", job_id=job_id, iterations=iteration)
                break

            affected = self._affected_service_ids(findings, plan)
            logger.info(
                "codegen_replanning",
                job_id=job_id,
                iteration=iteration,
                affected_services=sorted(affected),
                blocking_findings=len(findings),
            )
            self._report(job_id, min(80, 30 + iteration * 20), "service_planning")
            plan = self._plan(job_id, ctx, architecture, findings)

        # Finalize: patch architecture with the actual generated service ids
        generated_ids = list(services_codes.keys())
        architecture["generated_services"] = generated_ids
        architecture["iteration"] = iteration
        architecture["approved"] = bool(report and codegen_models.is_approved(report))
        self._save_artifact(job_id, "architecture_design", architecture, ArchitectureDesignerAgent().name, {})

        summary = {
            "job_id": job_id,
            "status": "generation_complete" if (report and codegen_models.is_approved(report)) else "generation_with_warnings",
            "iterations": iteration,
            "services_generated": generated_ids,
            "service_count": len(generated_ids),
            "review": report,
            "approved": bool(report and codegen_models.is_approved(report)),
            "history": self._history,
        }
        self._update_job(
            job_id,
            status="generation_complete",
            current_phase="generation_complete",
            progress=100,
        )
        self._report(job_id, 100, "finalize")

        # Cache summary in S3 for the UI
        self._store_summary(job_id, summary)
        return summary

    def _store_summary(self, job_id: str, summary: dict):
        """Persist the summary as a versioned artifact so the status endpoint can read it."""
        try:
            self._save_artifact(job_id, "codegen_summary", summary, "codegen_orchestrator", {})
        except Exception as exc:
            logger.warning("codegen_summary_store_failed", job_id=job_id, error=str(exc))


def json_loads(raw: bytes):
    import json

    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}
