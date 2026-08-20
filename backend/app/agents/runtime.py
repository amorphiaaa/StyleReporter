from __future__ import annotations

import json

from agents import Agent, Runner
from pydantic import BaseModel, Field

from app.domain.contracts import (
    AgentRunRequest,
    AgentRunResult,
    AgentRuntime,
    StyleReport,
    StyleReportRequest,
    StyleReportRuntime,
)

STYLE_METHODOLOGIST_INSTRUCTIONS = (
    "You are the StyleReporter style-methodologist agent. Work only from the "
    "questionnaire evidence provided in the input. Return a structured draft "
    "and do not invent missing client facts. This instruction set is a scaffold "
    "placeholder for the future methodology prompt."
)


class StyleReportAgentOutput(BaseModel):
    title: str
    summary: str
    observations: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class AgentsSdkStyleReportRuntime(StyleReportRuntime):
    """Agents SDK boundary with an explicit no-network dry-run mode."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key_configured: bool = False,
        dry_run: bool = True,
    ) -> None:
        self.model = model
        self.api_key_configured = api_key_configured
        self.dry_run = dry_run
        agent_kwargs: dict[str, object] = {
            "name": "Style methodologist",
            "instructions": STYLE_METHODOLOGIST_INSTRUCTIONS,
            "output_type": StyleReportAgentOutput,
        }
        if model:
            agent_kwargs["model"] = model
        self.agent = Agent(**agent_kwargs)

    async def generate(self, request: StyleReportRequest) -> StyleReport:
        if self.dry_run:
            return self._dry_run_report(request)
        if not self.api_key_configured:
            raise RuntimeError(
                "Agents SDK model calls require OPENAI_API_KEY; use agents_sdk_dry_run "
                "until credentials are configured."
            )

        result = await Runner.run(self.agent, _serialize_request(request))
        output = result.final_output_as(StyleReportAgentOutput)
        return StyleReport(
            report_version="agents-sdk-v1",
            runtime_type="agents_sdk",
            content=output.model_dump(mode="json"),
        )

    def _dry_run_report(self, request: StyleReportRequest) -> StyleReport:
        answered_fields = sorted(
            key
            for key, value in request.raw_payload.items()
            if value is not None and str(value).strip()
        )
        return StyleReport(
            report_version="agents-sdk-contract-v1",
            runtime_type="agents_sdk_dry_run",
            content={
                "title": "Agents SDK contract check",
                "summary": (
                    "The Agents SDK agent was constructed, but Runner.run was skipped. "
                    "No model call was made."
                ),
                "runtime": {
                    "agent_name": self.agent.name,
                    "model": self.model,
                    "dry_run": True,
                },
                "evidence": {
                    "source_submission_id": request.submission_id,
                    "answered_fields": answered_fields,
                },
            },
        )


def _serialize_request(request: StyleReportRequest) -> str:
    return json.dumps(
        {
            "client_id": request.client_id,
            "submission_id": request.submission_id,
            "questionnaire": dict(request.raw_payload),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


class ScaffoldAgentRuntime(AgentRuntime):
    """Placeholder for a future OpenAI Agents SDK Runner integration."""

    async def run(self, request: AgentRunRequest) -> AgentRunResult:
        raise NotImplementedError(
            "Agent execution is intentionally not implemented in the scaffold."
        )
