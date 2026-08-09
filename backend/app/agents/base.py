"""Agent base — definition-aware AI agent with Bedrock invocation and fallback."""

from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from app.ai.engine import AIEngine
from app.ai.service import get_ai_engine

logger = structlog.get_logger(__name__)

_DEFINITIONS_DIR = Path(__file__).parent / "definitions"


@dataclass
class AgentDefinition:
    """Metadata loaded from an agent definition markdown file."""
    agent_id: str = ""
    name: str = ""
    role: str = ""
    prompt_id: str = ""
    definition_file: str = ""
    content: str = ""
    output_artifact: str = ""
    model_role: str = "primary"
    expected_fields: list[str] = field(default_factory=list)
    max_iterations: int = 1

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "prompt_id": self.prompt_id,
            "definition_file": self.definition_file,
            "output_artifact": self.output_artifact,
            "model_role": self.model_role,
            "expected_fields": self.expected_fields,
            "max_iterations": self.max_iterations,
        }


class Agent:
    """Base class for all EMIP agents.

    Subclasses declare:
      - agent_id: unique identifier (e.g. 'architecture_designer')
      - definition_file: name of the markdown definition under agents/definitions/
      - prompt_id: prompt template id used for the runtime prompt
      - output_artifact: artifact type name produced by this agent
      - model_role: 'primary' or 'codegen' (selects the Bedrock model)
      - expected_fields: JSON fields that must be present in the AI response

    All Bedrock invocations go through AIEngine.invoke_ai_with_fallback() so the
    deterministic fallback chain always applies (project rule 10).
    """

    agent_id: str = ""
    definition_file: str = ""
    prompt_id: str = ""
    output_artifact: str = ""
    model_role: str = "primary"
    expected_fields: list[str] = []
    max_iterations: int = 1

    def __init__(self, engine: AIEngine | None = None):
        self._engine = engine or get_ai_engine()

    @property
    def engine(self) -> AIEngine:
        return self._engine

    @property
    def name(self) -> str:
        return self.agent_id or self.__class__.__name__

    def definition(self) -> AgentDefinition:
        """Load the markdown definition for this agent."""
        content = self.load_definition_text()
        return AgentDefinition(
            agent_id=self.agent_id,
            name=self.name,
            role=self._parse_role(content),
            prompt_id=self.prompt_id,
            definition_file=self.definition_file,
            content=content,
            output_artifact=self.output_artifact,
            model_role=self.model_role,
            expected_fields=self.expected_fields,
            max_iterations=self.max_iterations,
        )

    def load_definition_text(self) -> str:
        """Read the raw markdown definition file."""
        if not self.definition_file:
            return ""
        path = _DEFINITIONS_DIR / self.definition_file
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            logger.warning("agent_definition_missing", agent=self.agent_id, path=str(path))
            return ""

    def invoke(
        self,
        template_variables: dict,
        fallback_fn: Callable[[], Any] | None = None,
        job_id: str = "",
        response_type: str = "json_object",
        model_id: str | None = None,
        expected_fields: list[str] | None = None,
        max_tokens: int | None = None,
        prompt_id: str | None = None,
    ) -> tuple[Any, dict, bool]:
        """Invoke Bedrock with fallback through the AIEngine.

        Returns (result, metadata, used_ai) — see AIEngine.invoke_ai_with_fallback.
        """
        def _invoke() -> tuple[Any, dict, bool]:
            return self._engine.invoke_ai_with_fallback(
                prompt_id=prompt_id or self.prompt_id,
                template_variables=template_variables,
                fallback_fn=fallback_fn,
                response_type=response_type,
                expected_fields=expected_fields or self.expected_fields,
                model_id=model_id,
                job_id=job_id,
            )

        result, metadata, used_ai = _invoke()
        metadata["agent"] = self.agent_id
        return result, metadata, used_ai

    def _parse_role(self, content: str) -> str:
        """Extract the '## Role' section from the definition."""
        if not content:
            return ""
        lines = content.splitlines()
        in_role = False
        role_lines: list[str] = []
        for line in lines:
            if line.startswith("## Role"):
                in_role = True
                continue
            if in_role:
                if line.startswith("## "):
                    break
                role_lines.append(line)
        return " ".join(l.strip() for l in role_lines if l.strip())
