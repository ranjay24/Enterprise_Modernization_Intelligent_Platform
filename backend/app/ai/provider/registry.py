"""AI Provider Registry — central model selection and management."""

from __future__ import annotations

import structlog

from app.ai.cost.tracker import AICostTracker
from app.ai.provider.adapter import AIModelAdapter, AIModelResponse
from app.ai.provider.config import AIProviderConfig
from app.ai.provider.factory import ProviderFactory

logger = structlog.get_logger(__name__)


class ProviderRegistry:
    """Central registry for AI model providers.

    The orchestration layer must never directly instantiate model adapters.
    All model selection and invocation occurs through this registry.

    Supports:
    - Model selection by ID or role (primary/fallback)
    - Automatic fallback on failure
    - Cost tracking per invocation
    - Health checks across providers
    """

    def __init__(self, provider_config: AIProviderConfig):
        self._config = provider_config
        self._adapters: dict[str, AIModelAdapter] = {}
        self._cost_tracker = AICostTracker()

    @property
    def config(self) -> AIProviderConfig:
        return self._config

    @property
    def cost_tracker(self) -> AICostTracker:
        return self._cost_tracker

    def get_adapter(self, model_id: str | None = None) -> AIModelAdapter:
        """Get or create an adapter for the given model ID.

        If model_id is None, returns the primary model adapter.
        Adapters are cached after first creation.
        """
        key = model_id or self._config.default_model_id

        if key not in self._adapters:
            adapter = ProviderFactory.create_from_provider_config(self._config, model_id)
            self._adapters[key] = adapter

        return self._adapters[key]

    def get_primary_adapter(self) -> AIModelAdapter:
        return self.get_adapter(self._config.default_model_id)

    def get_fallback_adapter(self) -> AIModelAdapter:
        return self.get_adapter(self._config.fallback_model_id)

    def invoke(self, request, model_id: str | None = None) -> AIModelResponse:
        """Invoke a model with automatic fallback on failure.

        1. Try the requested model (or primary).
        2. On failure, try the fallback model.
        3. Track costs for successful invocations.
        """
        adapter = self.get_adapter(model_id)
        response = adapter.invoke(request)

        if response.success:
            self._cost_tracker.record_usage(
                model_id=response.model_id,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                latency_ms=response.latency_ms,
            )
            return response

        fallback_id = self._config.fallback_model_id
        if fallback_id and fallback_id != (model_id or self._config.default_model_id):
            logger.info(
                "invocation_fallback",
                failed_model=model_id or self._config.default_model_id,
                fallback_model=fallback_id,
                error=response.error,
            )
            fallback_adapter = self.get_adapter(fallback_id)
            fallback_response = fallback_adapter.invoke(request)
            fallback_response.is_fallback = True

            if fallback_response.success:
                self._cost_tracker.record_usage(
                    model_id=fallback_response.model_id,
                    input_tokens=fallback_response.input_tokens,
                    output_tokens=fallback_response.output_tokens,
                    latency_ms=fallback_response.latency_ms,
                )

            return fallback_response

        return response

    def health_check_all(self) -> dict[str, bool]:
        """Check health of all registered adapters."""
        results = {}
        for model_id, adapter in self._adapters.items():
            results[model_id] = adapter.health_check()
        return results

    def list_models(self) -> list[dict]:
        """List all configured models."""
        return [m.to_dict() for m in self._config.models if m.enabled]

    def clear_cache(self):
        """Clear cached adapters."""
        self._adapters.clear()
