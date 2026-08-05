"""Agent registry — catalog of all EMIP agents and their definitions."""

from __future__ import annotations

import structlog
from typing import TYPE_CHECKING

from app.agents.base import Agent

if TYPE_CHECKING:
    from app.agents.base import AgentDefinition

logger = structlog.get_logger(__name__)


class AgentRegistry:
    """Registers and exposes all agents participating in code generation.

    Agents register themselves via the ``@register_agent`` decorator or are added
    with ``register()``. The runtime uses the registry to resolve agents by id.
    """

    def __init__(self):
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> Agent:
        key = agent.agent_id
        if key in self._agents:
            logger.warning("agent_already_registered", agent_id=key)
        self._agents[key] = agent
        return agent

    def get(self, agent_id: str) -> Agent | None:
        return self._agents.get(agent_id)

    def require(self, agent_id: str) -> Agent:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise KeyError(f"Agent '{agent_id}' is not registered")
        return agent

    def all(self) -> list[Agent]:
        return list(self._agents.values())

    def definitions(self) -> list[dict]:
        return [a.definition().to_dict() for a in self._agents.values()]

    def clear(self):
        self._agents.clear()


_registry: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    """Return the process-wide agent registry (lazy singleton)."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
        _register_default_agents(_registry)
    return _registry


def _register_default_agents(registry: AgentRegistry):
    """Register the four code-generation agents."""
    from app.agents.architecture import ArchitectureDesignerAgent
    from app.agents.planner import ServicePlannerAgent
    from app.agents.generator import CodeGenerationAgent
    from app.agents.reviewer import ReviewAgent

    registry.register(ArchitectureDesignerAgent())
    registry.register(ServicePlannerAgent())
    registry.register(CodeGenerationAgent())
    registry.register(ReviewAgent())
