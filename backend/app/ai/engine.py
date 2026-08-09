"""AI Engine — central orchestration for AI-powered analysis.

Coordinates context building, prompt rendering, model invocation,
response validation, and result assembly across all AI capabilities.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from app.ai.capability_registry import CapabilityRegistry
from app.ai.context.builder import AIContext, AIContextBuilder
from app.ai.cost.tracker import AICostTracker
from app.ai.guardrails.validator import PromptValidator
from app.ai.observability.metrics import AIObservabilityMetrics
from app.ai.provider.config import AIProviderConfig
from app.ai.provider.registry import ProviderRegistry
from app.ai.validation.validator import AIResponseValidator
from app.core.analysis_profile import get_active_profile
from app.core.settings import get_settings
from app.prompts.templates.loader import PromptLoader
from app.prompts.templates.renderer import PromptRenderer

logger = structlog.get_logger(__name__)


class AIEngine:
    """Central AI engine coordinating all AI operations.

    Responsibilities:
    - Initialize and manage the provider registry
    - Build AI-ready context from Sprint 2 analysis
    - Render prompts via the prompt registry
    - Validate prompts through guardrails
    - Invoke foundation models through the provider layer
    - Validate and parse responses
    - Track costs and observability metrics
    - Route to deterministic fallbacks when AI fails
    """

    def __init__(self):
        self._settings = get_settings()
        self._profile = get_active_profile(self._settings.analysis_mode,
                                            self._settings.bedrock_max_tokens,
                                            self._settings.ai_prompt_max_tokens)
        self._provider_config = AIProviderConfig.from_settings(self._settings)
        self._provider_registry = ProviderRegistry(self._provider_config)
        self._context_builder = AIContextBuilder(profile=self._profile)
        self._prompt_loader = PromptLoader()
        self._prompt_renderer = PromptRenderer(self._prompt_loader)
        self._prompt_validator = PromptValidator(
            max_prompt_length=self._profile.prompt_max_tokens * 4
        )
        self._response_validator = AIResponseValidator()
        self._cost_tracker = self._provider_registry.cost_tracker
        self._observability = AIObservabilityMetrics()
        self._capability_registry = CapabilityRegistry()

        self._register_default_capabilities()

    def _register_default_capabilities(self):
        """Register built-in AI capabilities."""
        from app.ai.adr.generator import AIADRGenerator
        from app.ai.discovery.engine import AIMicroserviceDiscovery
        from app.ai.planner.engine import AIMigrationPlanner
        from app.ai.recommendation.engine import AIRecommendationEngine
        from app.ai.reports.developer import AIDeveloperReportGenerator
        from app.ai.reports.executive import AIExecutiveSummaryGenerator

        self._recommendation_engine = AIRecommendationEngine(self._provider_registry)
        self._adr_generator = AIADRGenerator()
        self._migration_planner = AIMigrationPlanner()
        self._discovery = AIMicroserviceDiscovery()
        self._executive_generator = AIExecutiveSummaryGenerator()
        self._developer_generator = AIDeveloperReportGenerator()

    @property
    def context_builder(self) -> AIContextBuilder:
        return self._context_builder

    @property
    def prompt_renderer(self) -> PromptRenderer:
        return self._prompt_renderer

    @property
    def provider_registry(self) -> ProviderRegistry:
        return self._provider_registry

    @property
    def cost_tracker(self) -> AICostTracker:
        return self._cost_tracker

    @property
    def observability(self) -> AIObservabilityMetrics:
        return self._observability

    @property
    def capability_registry(self) -> CapabilityRegistry:
        return self._capability_registry

    def invoke_ai(
        self,
        prompt_id: str,
        template_variables: dict,
        response_type: str = "json_object",
        expected_fields: list[str] | None = None,
        model_id: str | None = None,
        job_id: str = "",
        max_tokens: int | None = None,
    ) -> tuple[dict, dict]:
        if max_tokens is None:
            max_tokens = self._profile.bedrock_max_tokens
        """Execute a full AI invocation pipeline.

        Returns (parsed_response, metadata) tuple.
        parsed_response is the validated JSON dict from the model.
        metadata contains cost, latency, model, and token info.
        """
        metadata = {"stages": []}

        # Stage 1: Render prompt
        rendered_prompt, error = self._prompt_renderer.render_safe(prompt_id, template_variables)
        if error:
            logger.warning("prompt_render_failed", prompt_id=prompt_id, error=error)
            return {}, {"error": error, "stage": "prompt_render"}
        metadata["stages"].append("prompt_render")

        # Stage 2: Validate and sanitize prompt
        validation = self._prompt_validator.validate(rendered_prompt)
        if not validation.is_clean:
            logger.warning("prompt_validation_failed", violations=validation.violations)
            return {}, {"error": validation.violations, "stage": "prompt_validation"}
        prompt_to_send = validation.sanitized_content or rendered_prompt
        metadata["stages"].append("prompt_validation")

        # Stage 3: Invoke model
        from app.ai.provider.adapter import AIModelRequest

        request = AIModelRequest(
            prompt=prompt_to_send,
            max_tokens=max_tokens,
            model_id=model_id,
            expect_json=True,
            metadata={"job_id": job_id},
        )

        start = time.monotonic()
        response = self._provider_registry.invoke(request, model_id=model_id)
        latency_ms = (time.monotonic() - start) * 1000
        metadata["stages"].append("model_invocation")

        if not response.success:
            logger.warning("model_invocation_failed", error=response.error, model_id=response.model_id)
            return {}, {
                "error": response.error,
                "stage": "model_invocation",
                "model_id": response.model_id,
                "latency_ms": latency_ms,
            }

        # Stage 4: Record observability
        obs = self._observability.startObservation(prompt_id, response.model_id, job_id)
        obs.observation.prompt_tokens = response.input_tokens
        obs.observation.completion_tokens = response.output_tokens
        obs.observation.latency_ms = latency_ms
        obs.observation.estimated_cost = response.estimated_cost

        # Stage 5: Validate response
        response_validation = self._response_validator.validate(
            response.text, response_type, expected_fields
        )
        metadata["stages"].append("response_validation")

        metadata.update({
            "model_id": response.model_id,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "latency_ms": latency_ms,
            "estimated_cost": response.estimated_cost,
            "is_fallback": response.is_fallback,
            "validation": response_validation.to_dict(),
        })

        if not response_validation.is_valid:
            logger.warning("response_validation_failed", errors=response_validation.errors)
            metadata["error"] = "; ".join(response_validation.errors) or "response_validation_failed"
            return response_validation.parsed_data, metadata

        return response_validation.parsed_data, metadata

    def invoke_ai_with_fallback(
        self,
        prompt_id: str,
        template_variables: dict,
        fallback_fn=None,
        response_type: str = "json_object",
        expected_fields: list[str] | None = None,
        model_id: str | None = None,
        job_id: str = "",
    ) -> tuple[Any, dict, bool]:
        """Invoke AI with deterministic fallback.

        Returns (result, metadata, used_ai).
        used_ai is True if AI was used, False if fallback was used.
        """
        result, metadata = self.invoke_ai(
            prompt_id, template_variables, response_type, expected_fields, model_id, job_id
        )

        if result and not metadata.get("error"):
            return result, metadata, True

        if fallback_fn:
            logger.info("ai_fallback_triggered", prompt_id=prompt_id)
            fallback_result = fallback_fn()
            metadata["used_fallback"] = True
            return fallback_result, metadata, False

        return result, metadata, True

    def build_context(self, analysis_data: dict, job_id: str = "") -> AIContext:
        """Build AI-ready context from analysis data."""
        return self._context_builder.build(analysis_data, job_id)

    def build_graph_variables(self, analysis_data: dict) -> dict:
        """Build token-budgeted graph JSON variables for AI prompts.

        Carries the full static analysis graph (classes with dependencies,
        package tree, endpoints, dependency edges, injection deps, god
        classes, circular deps, detected business domains) into prompts
        instead of the old package-name-only summaries.
        """
        from app.ai.context.domains import build_graph_prompt_sections

        return build_graph_prompt_sections(analysis_data, self._profile)

    def get_health(self) -> dict:
        """Check health of AI subsystems."""
        return {
            "provider_registry": bool(self._provider_registry),
            "models": self._provider_registry.list_models(),
            "total_cost": self._cost_tracker.get_total_usage(),
            "failure_rate": self._observability.get_failure_rate(),
            "capabilities": len(self._capability_registry.list_all()),
        }
