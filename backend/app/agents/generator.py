"""Code Generation agent — generates a full Spring Boot service via Bedrock."""

from __future__ import annotations

import structlog
from typing import Any

from app.agents.base import Agent
from app.codegen import models as codegen_models
from app.codegen.project_builder import build_scaffold_service
from app.core.settings import get_settings

logger = structlog.get_logger(__name__)


class CodeGenerationAgent(Agent):
    """Generates one complete Maven + Spring Boot 3 + Java 17 microservice."""

    agent_id = "code_generation"
    definition_file = "codeGenerationAgent.md"
    prompt_id = "codegen/code_generator"
    output_artifact = "service_code"
    model_role = "codegen"
    expected_fields = ["files"]

    def model_id(self) -> str:
        """Code generation uses the dedicated codegen model."""
        settings = get_settings()
        return settings.bedrock_model_codegen

    def build_template_variables(
        self,
        service_plan: dict,
        source_boundary: dict,
        analysis_data: dict,
        regeneration_context: dict | None = None,
    ) -> dict:
        from app.ai.service import _compact_json

        settings = get_settings()
        return {
            "definition": self.load_definition_text(),
            "service_plan_json": _compact_json(service_plan, settings.ai_prompt_max_tokens),
            "source_boundary_json": _compact_json(source_boundary, settings.ai_prompt_max_tokens),
            "analysis_context_json": _compact_json(analysis_data, settings.ai_prompt_max_tokens),
            "regeneration_context_json": _compact_json(regeneration_context or {}, settings.ai_prompt_max_tokens),
        }

    def run(
        self,
        service_plan: dict,
        source_boundary: dict,
        analysis_data: dict,
        regeneration_context: dict | None = None,
        job_id: str = "",
    ) -> tuple[dict, dict, bool]:
        template_vars = self.build_template_variables(
            service_plan, source_boundary, analysis_data, regeneration_context
        )
        result, metadata, used_ai = self.invoke(
            template_variables=template_vars,
            fallback_fn=lambda: build_scaffold_service(service_plan),
            job_id=job_id,
            model_id=self.model_id(),
            expected_fields=self.expected_fields,
        )
        if isinstance(result, dict):
            result = codegen_models.normalize_service_code(result)
        else:
            result = build_scaffold_service(service_plan)
        return result, metadata, used_ai
