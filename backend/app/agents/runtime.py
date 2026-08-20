from __future__ import annotations

import json

from agents import Agent, Runner
from pydantic import BaseModel, Field

from app.agents.questionnaire_context import build_questionnaire_context
from app.domain.contracts import (
    AgentRunRequest,
    AgentRunResult,
    AgentRuntime,
    StyleReport,
    StyleReportRequest,
    StyleReportRuntime,
)

STYLE_METHODOLOGIST_INSTRUCTIONS = """
You are the StyleReporter style-methodologist agent.

Analyze one client's questionnaire evidence and return a structured draft with
exactly these goals:

1. CURRENT STYLE LANGUAGE: describe the style signals the client currently
   communicates, using only the evidence in the input.
2. DESIRED STYLE LANGUAGE: describe the style signals and feeling the client
   wants to communicate.
3. THE DISCONNECT: explain the actionable tension between current and desired
   style language. Separate direct evidence from reasonable interpretation.
4. YOUR ACTION PLAN: provide 3-5 concrete, observable actions the client can
   take. Each action needs a priority, focus, action, rationale, and first step.

Rules:
- Do not diagnose personality, psychology, body, identity, or lifestyle.
- Do not invent facts, wardrobe items, colors, brands, or image content.
- Treat missing fields as unknown and mention limitations in the output.
- Image URLs are metadata only; do not claim to have viewed the images.
- Keep advice practical, specific, non-shaming, and connected to the evidence.
""".strip()


class ActionPlanItem(BaseModel):
    priority: int = Field(ge=1, le=5)
    focus: str
    action: str
    rationale: str
    first_step: str


class StyleLanguageAnalysisOutput(BaseModel):
    title: str
    current_style_language: str
    desired_style_language: str
    disconnect: str
    your_action_plan: list[ActionPlanItem] = Field(min_length=3, max_length=5)
    evidence: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


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
            "output_type": StyleLanguageAnalysisOutput,
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
        output = result.final_output_as(StyleLanguageAnalysisOutput)
        return StyleReport(
            report_version="agents-sdk-v1",
            runtime_type="agents_sdk",
            content=output.model_dump(mode="json"),
        )

    def _dry_run_report(self, request: StyleReportRequest) -> StyleReport:
        context = build_questionnaire_context(request)
        normalized = context["normalized_answers"]
        current_style = normalized["current_style"] or "Current style language is not specified."
        style_goal = normalized["style_goal"] or "Desired style language is not specified."
        missing_fields = context["missing_report_fields"]
        output = StyleLanguageAnalysisOutput(
            title="Style Language analysis preview",
            current_style_language=(
                f"Current evidence: {current_style} "
                "This is a contract preview, not a model-generated interpretation."
            ),
            desired_style_language=(
                f"Desired evidence: {style_goal} "
                "This is a contract preview, not a model-generated interpretation."
            ),
            disconnect=(
                "Working hypothesis: compare the client's current style description "
                "with the desired feeling before choosing wardrobe actions."
            ),
            your_action_plan=[
                ActionPlanItem(
                    priority=1,
                    focus="Name the target signal",
                    action="Write three observable words for the desired style language.",
                    rationale="A clear target makes the current-to-desired gap actionable.",
                    first_step="Choose the three words that best match the desired feeling.",
                ),
                ActionPlanItem(
                    priority=2,
                    focus="Audit the current signal",
                    action="Review three recent outfits and note which signals repeat.",
                    rationale="Repeated choices reveal the current style language in practice.",
                    first_step="Photograph or list three outfits from the last two weeks.",
                ),
                ActionPlanItem(
                    priority=3,
                    focus="Run one controlled experiment",
                    action="Change one visible outfit signal toward the desired language.",
                    rationale=(
                        "A small experiment tests the direction without requiring a full "
                        "wardrobe change."
                    ),
                    first_step="Select one outfit and change only one styling decision.",
                ),
            ],
            evidence=[
                "The preview uses the typed questionnaire contract and persisted source evidence.",
            ],
            limitations=(
                [
                    "The Agents SDK model call was skipped.",
                    (
                        "A methodology prompt and human review are still required before "
                        "client delivery."
                    ),
                ]
                + [f"Missing questionnaire field: {field}" for field in missing_fields]
            ),
        )
        return StyleReport(
            report_version="agents-sdk-contract-v1",
            runtime_type="agents_sdk_dry_run",
            content={
                **output.model_dump(mode="json"),
                "summary": (
                    "The Agents SDK agent was constructed, but Runner.run was skipped. "
                    "No model call was made."
                ),
                "runtime": {
                    "agent_name": self.agent.name,
                    "model": self.model,
                    "dry_run": True,
                },
                "source_submission_id": request.submission_id,
            },
        )


def _serialize_request(request: StyleReportRequest) -> str:
    return json.dumps(
        {
            "client_id": request.client_id,
            "submission_id": request.submission_id,
            "questionnaire": build_questionnaire_context(request),
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
