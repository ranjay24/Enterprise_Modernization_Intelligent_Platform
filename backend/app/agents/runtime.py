"""Agent runtime — orchestrates the plan → build → review loop across agents."""

from __future__ import annotations

import structlog
from dataclasses import dataclass, field
from typing import Any, Callable

from app.agents.base import Agent

logger = structlog.get_logger(__name__)


@dataclass
class AgentIteration:
    """A single execution of an agent within the runtime loop."""
    iteration: int
    agent_id: str
    status: str = "pending"  # pending | running | completed | rejected | failed
    result: dict | None = None
    metadata: dict = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "iteration": self.iteration,
            "agent_id": self.agent_id,
            "status": self.status,
            "result": self.result,
            "metadata": self.metadata,
            "error": self.error,
        }


class AgentRuntime:
    """Runs agents in sequence with a bounded retry loop.

    Flow: planner (or architecture designer) → generator → reviewer. If the
    reviewer rejects the output, the loop replans with the reviewer's findings
    and regenerates, up to ``max_plan_iterations``.
    """

    def __init__(
        self,
        agents: list[Agent] | None = None,
        max_plan_iterations: int = 3,
        progress_callback: Callable[[str, int, str], None] | None = None,
    ):
        self._agents = list(agents or [])
        self._max_plan_iterations = max_plan_iterations
        self._progress_callback = progress_callback
        self._history: list[AgentIteration] = []

    @property
    def agents(self) -> list[Agent]:
        return list(self._agents)

    @property
    def history(self) -> list[AgentIteration]:
        return list(self._history)

    def add_agent(self, agent: Agent):
        self._agents.append(agent)

    def _report(self, job_id: str, progress: int, stage: str):
        if self._progress_callback:
            try:
                self._progress_callback(job_id, progress, stage)
            except Exception:
                pass

    def run_agent(
        self,
        agent: Agent,
        iteration: int,
        template_variables: dict,
        fallback_fn=None,
        job_id: str = "",
        model_id: str | None = None,
        expected_fields: list[str] | None = None,
    ) -> AgentIteration:
        """Execute a single agent with its fallback and record the result."""
        entry = AgentIteration(iteration=iteration, agent_id=agent.agent_id, status="running")
        self._history.append(entry)
        self._report(job_id, 0, f"{agent.agent_id}_started")

        try:
            result, metadata, used_ai = agent.invoke(
                template_variables=template_variables,
                fallback_fn=fallback_fn,
                job_id=job_id,
                model_id=model_id,
                expected_fields=expected_fields,
            )
            entry.result = result
            entry.metadata = metadata
            entry.status = "completed"
            self._report(job_id, 0, f"{agent.agent_id}_completed")
        except Exception as exc:
            entry.status = "failed"
            entry.error = str(exc)
            logger.error("agent_run_failed", agent=agent.agent_id, iteration=iteration, error=str(exc))

        return entry

    def run_loop(self):
        """The plan→build→review loop is implemented by CodeGenOrchestrator."""
        raise NotImplementedError("run_loop is implemented by CodeGenOrchestrator")
