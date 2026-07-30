"""Prompt Renderer — renders prompt templates with variable substitution."""

from __future__ import annotations

import re

import structlog

from app.prompts.templates.loader import PromptLoader, PromptTemplate

logger = structlog.get_logger(__name__)


class PromptRenderer:
    """Renders prompt templates by substituting variables.

    Supports:
    - Simple {{variable}} substitution
    - Default values via {{variable|default_value}}
    - Conditional sections via {% if condition %}...{% endif %}
    - Nested variable access via dot notation
    """

    VARIABLE_PATTERN = re.compile(r"\{\{(\w+)(?:\|([^}]*))?\}\}")
    CONDITIONAL_START = re.compile(r"\{%\s*if\s+(\w+)\s*%\}")
    CONDITIONAL_END = re.compile(r"\{%\s*endif\s*%\}")

    def __init__(self, loader: PromptLoader | None = None):
        self._loader = loader or PromptLoader()

    def render(self, template: PromptTemplate, variables: dict) -> str:
        """Render a prompt template with the given variables."""
        content = template.content
        content = self._render_conditionals(content, variables)
        content = self._render_variables(content, variables)
        return content

    def render_by_id(self, prompt_id: str, variables: dict) -> str:
        """Load and render a prompt template by ID."""
        template = self._loader.load(prompt_id)
        if template is None:
            raise ValueError(f"Prompt template not found: {prompt_id}")
        return self.render(template, variables)

    def render_safe(self, prompt_id: str, variables: dict) -> tuple[str, str]:
        """Render with fallback — returns (rendered_prompt, error_string).

        Used by pipeline stages that should not fail on missing prompts.
        """
        try:
            template = self._loader.load(prompt_id)
            if template is None:
                return "", f"Template not found: {prompt_id}"
            return self.render(template, variables), ""
        except Exception as exc:
            logger.error("prompt_render_failed", prompt_id=prompt_id, error=str(exc))
            return "", str(exc)

    def _render_variables(self, content: str, variables: dict) -> str:
        """Substitute {{variable}} and {{variable|default}} patterns."""
        def _replace(match):
            var_name = match.group(1)
            default = match.group(2)
            value = variables.get(var_name)
            if value is not None:
                return str(value)
            if default is not None:
                return default
            logger.warning("prompt_variable_missing", variable=var_name)
            return f"[MISSING:{var_name}]"

        return self.VARIABLE_PATTERN.sub(_replace, content)

    def _render_conditionals(self, content: str, variables: dict) -> str:
        """Render {% if variable %}...{% endif %} blocks."""
        result = content
        while self.CONDITIONAL_START.search(result):
            match = self.CONDITIONAL_START.search(result)
            if not match:
                break

            var_name = match.group(1)
            start_pos = match.start()
            end_match = self.CONDITIONAL_END.search(result, match.end())

            if not end_match:
                logger.warning("unclosed_conditional", variable=var_name)
                result = result[:start_pos] + result[match.end():]
                continue

            block_content = result[match.end():end_match.start()]
            condition_value = variables.get(var_name, False)

            if condition_value:
                replacement = block_content
            else:
                replacement = ""

            result = result[:start_pos] + replacement + result[end_match.end():]

        return result

    def validate_template(self, template: PromptTemplate, variables: dict) -> list[str]:
        """Validate that all required variables are provided.

        Returns list of missing variable names.
        """
        required = set(self.VARIABLE_PATTERN.findall(template.content))
        missing = []
        for var_name, default in required:
            if var_name not in variables and not default:
                missing.append(var_name)
        return missing
