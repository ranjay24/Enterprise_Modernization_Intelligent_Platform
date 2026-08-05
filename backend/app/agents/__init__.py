"""Agent framework — definition-driven AI agents for service code generation.

Every agent is defined by a markdown definition file (backend/app/agents/definitions/)
and executed by a runtime class that invokes Amazon Bedrock (Nova) through the
AIEngine fallback chain. Rules 6/7/10 of AGENTS.md apply: all invocations flow
through the AIEngine and always carry a deterministic fallback.
"""

from app.agents.base import Agent, AgentDefinition
from app.agents.registry import AgentRegistry, get_agent_registry
from app.agents.runtime import AgentRuntime, AgentIteration

__all__ = [
    "Agent",
    "AgentDefinition",
    "AgentRegistry",
    "get_agent_registry",
    "AgentRuntime",
    "AgentIteration",
]
