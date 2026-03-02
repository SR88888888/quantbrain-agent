import time
from abc import ABC, abstractmethod
from typing import Dict, Any
from src.domain.models import AgentRole, AgentOutput


class BaseAgent(ABC):

    def __init__(self, role: AgentRole):
        self.role = role

    @abstractmethod
    async def run(self, context: Dict[str, Any]) -> AgentOutput:
        pass

    def _output(
        self,
        data: Dict[str, Any],
        reasoning_chain: list = None,
        skills_used: list = None,
        data_quality: float = 1.0,
        error: str = None,
    ) -> AgentOutput:
        return AgentOutput(
            agent_role=self.role,
            success=error is None,
            data=data,
            reasoning_chain=reasoning_chain or [],
            skills_used=skills_used or [],
            data_quality=data_quality,
            error=error,
        )

    def _error_output(self, message: str) -> AgentOutput:
        return self._output(data={}, error=message, data_quality=0.0)
