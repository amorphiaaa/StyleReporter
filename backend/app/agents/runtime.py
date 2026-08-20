from app.domain.contracts import AgentRunRequest, AgentRunResult, AgentRuntime


class ScaffoldAgentRuntime(AgentRuntime):
    """Placeholder for a future OpenAI Agents SDK Runner integration."""

    async def run(self, request: AgentRunRequest) -> AgentRunResult:
        raise NotImplementedError(
            "Agent execution is intentionally not implemented in the scaffold."
        )
