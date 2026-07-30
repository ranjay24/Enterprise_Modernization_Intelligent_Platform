"""AI Provider Factory — creates model adapters from configuration."""

from __future__ import annotations

import structlog

from app.ai.provider.adapter import AIModelAdapter
from app.ai.provider.config import AIModelConfig, AIProviderConfig

logger = structlog.get_logger(__name__)

_ADAPTER_REGISTRY: dict[str, type[AIModelAdapter]] = {}


def register_adapter(provider: str, adapter_class: type[AIModelAdapter]):
    """Register an adapter class for a provider name."""
    _ADAPTER_REGISTRY[provider] = adapter_class


def _load_builtin_adapters():
    """Lazy-load built-in adapters."""
    if "bedrock" not in _ADAPTER_REGISTRY:
        from app.ai.provider.nova import NovaAdapter
        _ADAPTER_REGISTRY["bedrock"] = NovaAdapter


class ProviderFactory:
    """Creates model adapters from configuration.

    The factory never hardcodes model IDs. All model selection occurs through
    AIProviderConfig which is built from application settings.
    """

    @staticmethod
    def create(config: AIModelConfig) -> AIModelAdapter:
        """Create a model adapter for the given configuration."""
        _load_builtin_adapters()

        adapter_class = _ADAPTER_REGISTRY.get(config.provider)
        if adapter_class is None:
            raise ValueError(
                f"No adapter registered for provider '{config.provider}'. "
                f"Available: {list(_ADAPTER_REGISTRY.keys())}"
            )

        logger.info(
            "adapter_created",
            provider=config.provider,
            model_id=config.model_id,
            display_name=config.display_name,
        )
        return adapter_class(config)

    @staticmethod
    def create_from_provider_config(
        provider_config: AIProviderConfig,
        model_id: str | None = None,
    ) -> AIModelAdapter:
        """Create an adapter using the provider config to resolve the model."""
        if model_id:
            model_config = provider_config.get_model(model_id)
        else:
            model_config = provider_config.get_primary()

        if model_config is None:
            raise ValueError(
                f"No enabled model found for ID '{model_id}'. "
                f"Available: {[m.model_id for m in provider_config.models if m.enabled]}"
            )

        return ProviderFactory.create(model_config)

    @staticmethod
    def create_fallback(provider_config: AIProviderConfig) -> AIModelAdapter:
        """Create an adapter for the fallback model."""
        fallback = provider_config.get_fallback()
        if fallback is None:
            raise ValueError("No fallback model configured")
        return ProviderFactory.create(fallback)
