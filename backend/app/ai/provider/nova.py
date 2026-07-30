"""Amazon Nova adapter — Bedrock converse API integration."""

from __future__ import annotations

import structlog

from app.ai.provider.adapter import AIModelAdapter, AIModelRequest, AIModelResponse
from app.ai.provider.config import AIModelConfig
from app.aws.clients import AWSClients
from app.core.settings import get_settings

logger = structlog.get_logger(__name__)


class NovaAdapter(AIModelAdapter):
    """Amazon Nova model adapter using Bedrock converse API."""

    def __init__(self, config: AIModelConfig):
        super().__init__(config)
        self._settings = get_settings()
        self._clients: AWSClients | None = None

    @property
    def _bedrock(self):
        if self._clients is None:
            self._clients = AWSClients(settings=self._settings)
        return self._clients.bedrock

    def invoke(self, request: AIModelRequest) -> AIModelResponse:
        model_id = request.model_id or self._config.model_id
        messages = [{"role": "user", "content": [{"text": request.prompt}]}]

        inference_config = {
            "maxTokens": min(request.max_tokens, self._config.max_tokens),
            "temperature": request.temperature if request.temperature > 0 else self._config.temperature,
        }

        try:
            response = self._bedrock.converse(
                modelId=model_id,
                messages=messages,
                inferenceConfig=inference_config,
            )

            output = response.get("output", {}).get("message", {}).get("content", [])
            text = output[0]["text"] if output else ""

            usage = response.get("usage", {})
            input_tokens = usage.get("inputTokens", 0)
            output_tokens = usage.get("outputTokens", 0)

            return AIModelResponse(
                text=text,
                model_id=model_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                finish_reason=response.get("stopReason", "stop"),
                raw_response=response,
            )

        except Exception as exc:
            logger.warning("nova_invoke_failed", model_id=model_id, error=str(exc))
            return AIModelResponse(
                text="",
                model_id=model_id,
                error=str(exc),
            )

    def health_check(self) -> bool:
        try:
            response = self._bedrock.converse(
                modelId=self._config.model_id,
                messages=[{"role": "user", "content": [{"text": "ping"}]}],
                inferenceConfig={"maxTokens": 10, "temperature": 0.0},
            )
            return "output" in response
        except Exception:
            return False

    def supported_features(self) -> list[str]:
        features = ["json_mode", "code_generation"]
        if self._config.supports_vision:
            features.append("vision")
        return features
