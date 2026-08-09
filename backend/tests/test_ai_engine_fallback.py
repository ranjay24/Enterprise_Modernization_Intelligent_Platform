"""Regression tests for the AI engine fallback path.

Root-cause guard (codegen "no Java sources generated" bug):
When Bedrock returns output that fails response validation (e.g. truncated
JSON on a full-service codegen call), invoke_ai_with_fallback must route to
the deterministic fallback instead of returning the validation garbage
({"raw_response": ...}) as if it were valid AI output.
"""

import pytest

from app.ai.engine import AIEngine
from app.ai.provider.adapter import AIModelResponse


def _template_vars() -> dict:
    return {
        "definition": "You are a code generator.",
        "service_plan_json": "{}",
        "source_boundary_json": "{}",
        "analysis_context_json": "{}",
        "regeneration_context_json": "{}",
    }


def _engine_with_text(monkeypatch, text: str) -> AIEngine:
    engine = AIEngine()

    def fake_invoke(request, model_id=None):
        return AIModelResponse(
            text=text,
            model_id=model_id or "amazon.nova-pro-v1:0",
            input_tokens=10,
            output_tokens=len(text),
        )

    monkeypatch.setattr(engine.provider_registry, "invoke", fake_invoke)
    return engine


class TestInvokeAiValidation:
    def test_invalid_json_sets_metadata_error(self, monkeypatch):
        engine = _engine_with_text(monkeypatch, "this is not valid json {{{")
        _, metadata, _ = engine.invoke_ai_with_fallback(
            prompt_id="codegen/code_generator",
            template_variables=_template_vars(),
            fallback_fn=lambda: {"files": [{"path": "pom.xml", "content": "<x/>"}]},
        )
        assert "error" in metadata, "validation failure must be surfaced as metadata error"

    def test_invalid_json_triggers_fallback(self, monkeypatch):
        fallback_called = []

        def fallback():
            fallback_called.append(True)
            return {"files": [{"path": "src/main/java/Fallback.java", "content": "class F {}"}]}

        engine = _engine_with_text(monkeypatch, "not json {{{")
        result, metadata, used_ai = engine.invoke_ai_with_fallback(
            prompt_id="codegen/code_generator",
            template_variables=_template_vars(),
            fallback_fn=fallback,
        )
        assert used_ai is False
        assert metadata.get("used_fallback") is True
        assert fallback_called == [True]
        assert result["files"][0]["path"] == "src/main/java/Fallback.java"

    def test_missing_expected_field_triggers_fallback(self, monkeypatch):
        engine = _engine_with_text(monkeypatch, '{"service_id": "x"}')
        result, metadata, used_ai = engine.invoke_ai_with_fallback(
            prompt_id="codegen/code_generator",
            template_variables=_template_vars(),
            fallback_fn=lambda: {"files": []},
            expected_fields=["files"],
        )
        assert used_ai is False
        assert result == {"files": []}
        assert "error" in metadata

    def test_valid_json_uses_ai_not_fallback(self, monkeypatch):
        valid = '{"service_id": "order", "files": [{"path": "pom.xml", "content": "<x/>"}]}'
        engine = _engine_with_text(monkeypatch, valid)
        result, metadata, used_ai = engine.invoke_ai_with_fallback(
            prompt_id="codegen/code_generator",
            template_variables=_template_vars(),
            fallback_fn=lambda: {"files": []},
            expected_fields=["files"],
        )
        assert used_ai is True
        assert "error" not in metadata
        assert result["service_id"] == "order"
