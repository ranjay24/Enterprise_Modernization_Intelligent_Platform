"""AI Model Adapter — abstract base for foundation model integrations."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import structlog

from app.ai.provider.config import AIModelConfig

logger = structlog.get_logger(__name__)


@dataclass
class AIModelRequest:
    """A request to a foundation model."""
    prompt: str = ""
    system_prompt: str = ""
    max_tokens: int = 8000
    temperature: float = 0.0
    model_id: str | None = None
    expect_json: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class AIModelResponse:
    """Response from a foundation model."""
    text: str = ""
    model_id: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    finish_reason: str = "stop"
    is_fallback: bool = False
    raw_response: dict | None = None
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.text)

    @property
    def estimated_cost(self) -> float:
        from app.ai.cost.tracker import AICostTracker
        return AICostTracker.estimate_cost(
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            model_id=self.model_id,
        )


class AIModelAdapter(ABC):
    """Abstract base class for foundation model adapters.

    All model integrations (Nova, Claude, Llama, etc.) implement this interface.
    The orchestration layer never directly instantiates adapters — it uses the
    ProviderRegistry which delegates to the ProviderFactory.
    """

    def __init__(self, config: AIModelConfig):
        self._config = config
        self._name = config.provider

    @property
    def name(self) -> str:
        return self._name

    @property
    def config(self) -> AIModelConfig:
        return self._config

    @abstractmethod
    def invoke(self, request: AIModelRequest) -> AIModelResponse:
        """Invoke the foundation model with a request.

        Must handle:
        - Connection errors (raise to allow retry at adapter level)
        - Timeout errors (raise to allow retry)
        - Rate limiting (raise to allow backoff)
        - Invalid responses (return error in response)
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the model is available and responsive."""
        ...

    @abstractmethod
    def supported_features(self) -> list[str]:
        """Return list of supported features (e.g., 'json_mode', 'vision')."""
        ...

    def _measure_latency(self, func, *args, **kwargs) -> tuple:
        """Measure execution latency of a function call."""
        start = time.monotonic()
        try:
            result = func(*args, **kwargs)
            elapsed = (time.monotonic() - start) * 1000
            return result, elapsed
        except Exception:
            elapsed = (time.monotonic() - start) * 1000
            raise
