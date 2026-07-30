"""AI Pipeline — explicit stages for AI analysis orchestration.

Pipeline flow:
Context Builder → Prompt Builder → Prompt Validator → Provider Registry
→ Foundation Model Adapter → Response Validator → Recommendation Builder → Formatter

Avoids embedding all orchestration logic inside one file.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""
    success: bool = True
    stages_completed: list[str] = field(default_factory=list)
    stage_results: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    total_latency_ms: float = 0.0
    model_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "stages_completed": self.stages_completed,
            "errors": self.errors,
            "total_latency_ms": self.total_latency_ms,
            "model_id": self.model_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


class PipelineStage(ABC):
    """Abstract base for a pipeline stage."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stage name for logging and tracking."""
        ...

    @abstractmethod
    def execute(self, state: dict) -> dict:
        """Execute this stage, modifying and returning the pipeline state."""
        ...

    def validate_input(self, state: dict) -> list[str]:
        """Validate required inputs are present. Returns list of missing items."""
        return []


class ContextBuilderStage(PipelineStage):
    """Stage 1: Build AI-ready context from analysis data."""
    name = "context_builder"

    def __init__(self, context_builder):
        self._builder = context_builder

    def execute(self, state: dict) -> dict:
        analysis_data = state.get("analysis_data", {})
        job_id = state.get("job_id", "")
        ai_context = self._builder.build(analysis_data, job_id=job_id)
        state["ai_context"] = ai_context
        state["template_variables"] = ai_context.to_template_variables()
        return state


class PromptBuilderStage(PipelineStage):
    """Stage 2: Render prompt template with context variables."""
    name = "prompt_builder"

    def __init__(self, renderer):
        self._renderer = renderer

    def execute(self, state: dict) -> dict:
        prompt_id = state.get("prompt_id", "")
        template_variables = state.get("template_variables", {})

        rendered, error = self._renderer.render_safe(prompt_id, template_variables)
        if error:
            state["prompt"] = ""
            state.setdefault("errors", []).append(f"Prompt render failed: {error}")
        else:
            state["prompt"] = rendered

        state["prompt_id"] = prompt_id
        return state


class PromptValidatorStage(PipelineStage):
    """Stage 3: Validate prompt before sending to model."""
    name = "prompt_validator"

    def __init__(self, validator):
        self._validator = validator

    def execute(self, state: dict) -> dict:
        prompt = state.get("prompt", "")
        system_prompt = state.get("system_prompt", "")

        if not prompt:
            state["prompt_valid"] = False
            state.setdefault("errors", []).append("Empty prompt")
            return state

        result = self._validator.validate(prompt, system_prompt)
        state["prompt_valid"] = result.is_clean
        state["sanitized_prompt"] = result.sanitized_content if result.sanitized_content else prompt
        state["guardrail_warnings"] = result.warnings

        if not result.is_clean:
            state.setdefault("errors", []).extend(result.violations)

        return state


class ProviderInvocationStage(PipelineStage):
    """Stage 4: Invoke the foundation model via provider registry."""
    name = "provider_invocation"

    def __init__(self, provider_registry):
        self._registry = provider_registry

    def execute(self, state: dict) -> dict:
        from app.ai.provider.adapter import AIModelRequest

        prompt = state.get("sanitized_prompt", state.get("prompt", ""))
        system_prompt = state.get("system_prompt", "")
        model_id = state.get("model_id")

        request = AIModelRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=state.get("max_tokens", 8000),
            temperature=state.get("temperature", 0.0),
            model_id=model_id,
            expect_json=state.get("expect_json", True),
        )

        start = time.monotonic()
        response = self._registry.invoke(request, model_id=model_id)
        elapsed = (time.monotonic() - start) * 1000

        state["model_response"] = response
        state["response_text"] = response.text
        state["model_id"] = response.model_id
        state["input_tokens"] = response.input_tokens
        state["output_tokens"] = response.output_tokens
        state["latency_ms"] = elapsed

        if not response.success:
            state.setdefault("errors", []).append(f"Model invocation failed: {response.error}")

        return state


class ResponseValidatorStage(PipelineStage):
    """Stage 5: Validate model response."""
    name = "response_validator"

    def __init__(self, response_validator):
        self._validator = response_validator

    def execute(self, state: dict) -> dict:
        response_text = state.get("response_text", "")
        response_type = state.get("response_type", "generic")
        expected_fields = state.get("expected_fields", [])

        result = self._validator.validate(response_text, response_type, expected_fields)
        state["response_valid"] = result.is_valid
        state["parsed_response"] = result.parsed_data
        state["validation_errors"] = result.errors

        if not result.is_valid:
            state.setdefault("errors", []).extend(result.errors)

        return state


class RecommendationBuilderStage(PipelineStage):
    """Stage 6: Build typed recommendation objects from validated response."""
    name = "recommendation_builder"

    def execute(self, state: dict) -> dict:
        parsed = state.get("parsed_response", {})
        response_type = state.get("response_type", "generic")

        if not parsed:
            state["built_result"] = None
            return state

        builder = state.get("result_builder")
        if builder:
            state["built_result"] = builder(parsed, state)
        else:
            state["built_result"] = parsed

        return state


class FormatterStage(PipelineStage):
    """Stage 7: Format final output for storage and API response."""
    name = "formatter"

    def execute(self, state: dict) -> dict:
        built_result = state.get("built_result")
        if built_result and hasattr(built_result, "to_dict"):
            state["final_output"] = built_result.to_dict()
        elif built_result:
            state["final_output"] = built_result
        else:
            state["final_output"] = {}

        state["pipeline_result"] = PipelineResult(
            success=not state.get("errors"),
            stages_completed=state.get("stages_completed", []),
            errors=state.get("errors", []),
            total_latency_ms=state.get("latency_ms", 0),
            model_id=state.get("model_id", ""),
            input_tokens=state.get("input_tokens", 0),
            output_tokens=state.get("output_tokens", 0),
        )

        return state


class AIPipeline:
    """Orchestrates a sequence of pipeline stages.

    Each stage receives and returns a shared state dict.
    Stages can be added, removed, or reordered.
    """

    def __init__(self):
        self._stages: list[PipelineStage] = []

    def add_stage(self, stage: PipelineStage) -> AIPipeline:
        """Add a stage to the pipeline."""
        self._stages.append(stage)
        return self

    def add_stages(self, stages: list[PipelineStage]) -> AIPipeline:
        """Add multiple stages."""
        for stage in stages:
            self._stages.append(stage)
        return self

    def remove_stage(self, name: str) -> AIPipeline:
        """Remove a stage by name."""
        self._stages = [s for s in self._stages if s.name != name]
        return self

    def execute(self, initial_state: dict) -> PipelineResult:
        """Execute all pipeline stages in order."""
        state = dict(initial_state)
        state["stages_completed"] = []
        state["errors"] = []

        start = time.monotonic()

        for stage in self._stages:
            stage_name = stage.name
            try:
                unmet = stage.validate_input(state)
                if unmet:
                    logger.warning("stage_prerequisites_unmet", stage=stage_name, missing=unmet)
                    state.setdefault("errors", []).append(f"Stage {stage_name}: missing {unmet}")
                    continue

                state = stage.execute(state)
                state["stages_completed"].append(stage_name)

            except Exception as exc:
                logger.error("stage_failed", stage=stage_name, error=str(exc))
                state.setdefault("errors", []).append(f"Stage {stage_name} failed: {exc!s}")

        elapsed = (time.monotonic() - start) * 1000

        return PipelineResult(
            success=not state.get("errors"),
            stages_completed=state.get("stages_completed", []),
            stage_results={k: v for k, v in state.items() if k.startswith("stage_")},
            errors=state.get("errors", []),
            total_latency_ms=elapsed,
            model_id=state.get("model_id", ""),
            input_tokens=state.get("input_tokens", 0),
            output_tokens=state.get("output_tokens", 0),
        )

    @property
    def stages(self) -> list[str]:
        return [s.name for s in self._stages]
