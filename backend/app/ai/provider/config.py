"""AI Provider configuration — model configuration without hardcoded IDs."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AIModelConfig:
    """Configuration for a single foundation model."""
    model_id: str = ""
    provider: str = ""
    display_name: str = ""
    max_tokens: int = 8000
    temperature: float = 0.0
    top_p: float = 1.0
    supports_system_prompt: bool = True
    supports_json_mode: bool = True
    supports_vision: bool = False
    supports_code_generation: bool = True
    supports_conversation: bool = False
    cost_per_input_token: float = 0.0
    cost_per_output_token: float = 0.0
    is_primary: bool = False
    is_fallback: bool = False
    priority: int = 100
    enabled: bool = True
    extra_params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "display_name": self.display_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "supports_system_prompt": self.supports_system_prompt,
            "supports_json_mode": self.supports_json_mode,
            "cost_per_input_token": self.cost_per_input_token,
            "cost_per_output_token": self.cost_per_output_token,
            "is_primary": self.is_primary,
            "is_fallback": self.is_fallback,
            "enabled": self.enabled,
        }


@dataclass
class AIProviderConfig:
    """Configuration for the AI provider layer."""
    models: list[AIModelConfig] = field(default_factory=list)
    default_model_id: str = ""
    fallback_model_id: str = ""
    max_retries: int = 3
    retry_base_delay: float = 1.0
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    enable_cost_tracking: bool = True
    enable_observability: bool = True
    prompt_max_tokens: int = 7000
    response_timeout_seconds: int = 60

    @classmethod
    def from_settings(cls, settings) -> AIProviderConfig:
        """Build provider config from application settings."""
        from app.core.analysis_profile import get_active_profile
        profile = get_active_profile(settings.analysis_mode,
                                      settings.bedrock_max_tokens,
                                      settings.ai_prompt_max_tokens)
        output_tokens = profile.bedrock_max_tokens
        prompt_tokens = profile.prompt_max_tokens

        models = [
            AIModelConfig(
                model_id=settings.bedrock_model_primary,
                provider="bedrock",
                display_name="Amazon Nova Pro",
                max_tokens=output_tokens,
                temperature=0.0,
                is_primary=True,
                priority=1,
                cost_per_input_token=0.0008 / 1000,
                cost_per_output_token=0.0016 / 1000,
            ),
            AIModelConfig(
                model_id=settings.bedrock_model_fallback,
                provider="bedrock",
                display_name="Amazon Nova Lite",
                max_tokens=output_tokens,
                temperature=0.0,
                is_fallback=True,
                priority=2,
                cost_per_input_token=0.00006 / 1000,
                cost_per_output_token=0.00024 / 1000,
            ),
        ]

        return cls(
            models=models,
            default_model_id=settings.bedrock_model_primary,
            fallback_model_id=settings.bedrock_model_fallback,
            max_retries=settings.bedrock_max_retries,
            prompt_max_tokens=prompt_tokens,
        )

    def get_model(self, model_id: str | None = None) -> AIModelConfig | None:
        """Get a model config by ID, or the default."""
        target = model_id or self.default_model_id
        for m in self.models:
            if m.model_id == target and m.enabled:
                return m
        return None

    def get_primary(self) -> AIModelConfig | None:
        for m in self.models:
            if m.is_primary and m.enabled:
                return m
        return self.models[0] if self.models else None

    def get_fallback(self) -> AIModelConfig | None:
        for m in self.models:
            if m.is_fallback and m.enabled:
                return m
        return None
