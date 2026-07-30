"""Bedrock AI client with retry and fallback logic — uses converse API."""

import time

import structlog

from app.aws.clients import AWSClients
from app.core.settings import get_settings

logger = structlog.get_logger(__name__)

BASE_DELAY = 1.0


class BedrockRepository:
    """Bedrock Runtime API operations with retry and fallback using converse API."""

    def __init__(self):
        self._settings = get_settings()
        self._clients = AWSClients(settings=self._settings)

    def invoke(
        self,
        prompt: str,
        max_tokens: int | None = None,
        model_id: str | None = None,
    ) -> str:
        """Invoke Bedrock converse API with retry and fallback."""
        model = model_id or self._settings.bedrock_model_primary
        if max_tokens is None:
            from app.core.analysis_profile import get_active_profile
            profile = get_active_profile(self._settings.analysis_mode,
                                          self._settings.bedrock_max_tokens,
                                          self._settings.ai_prompt_max_tokens)
            tokens = profile.bedrock_max_tokens
        else:
            tokens = max_tokens

        last_error = None
        for attempt in range(self._settings.bedrock_max_retries):
            try:
                response = self._clients.bedrock.converse(
                    modelId=model,
                    messages=[{"role": "user", "content": [{"text": prompt}]}],
                    inferenceConfig={"maxTokens": tokens, "temperature": 0.0},
                )
                output = response["output"]["message"]["content"]
                return output[0]["text"]
            except Exception as exc:
                last_error = exc
                delay = BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "bedrock_call_failed",
                    model=model,
                    attempt=attempt + 1,
                    max_retries=self._settings.bedrock_max_retries,
                    error=str(exc),
                )
                if attempt < self._settings.bedrock_max_retries - 1:
                    time.sleep(delay)

        if model != self._settings.bedrock_model_fallback:
            logger.info("falling_back_to_model", model=self._settings.bedrock_model_fallback)
            return self.invoke(
                prompt,
                max_tokens=tokens,
                model_id=self._settings.bedrock_model_fallback,
            )

        raise last_error
