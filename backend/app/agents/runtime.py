from __future__ import annotations

import json

import httpx
from agents import Agent, Runner
from pydantic import BaseModel, ConfigDict, Field

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
You are the senior personal stylist and client-facing writer for StyleReporter.

Your job is not to repeat questionnaire answers. Your job is to recognise the
pattern across what the client said, what repeats in the attached images, and
what the client wants to feel, then explain that pattern in warm, plain English.
The finished report should feel like an insightful stylist is speaking directly
to the client: specific, kind, memorable, and useful without a stylist present.

Use this reasoning sequence before writing:

1. Extract direct evidence separately from questionnaire answers, repeated
   visual observations, desired feelings, and constraints. Treat repeated
   signals as stronger than one isolated preference.
2. Interpret the pattern. Explain what the client's current wardrobe is doing
   for them, what it communicates, and where it stops short of the desired
   feeling. This is the analysis layer; do not merely paraphrase the input.
3. Translate the interpretation into a small Style Language: five current
   words, five desired words, a memorable two-to-four-word name, three anchor
   words, and a plain-English explanation.
4. Turn the disconnect into exactly three prioritised actions. Each action must
   explain the principle, why it closes this client's gap, how to apply it, and
   what to try first.

Write the report in second person. Use the supplied families (Effortless,
Creative, Intentional, and Polished/Refined) only as calibration examples; they
are not a mandatory taxonomy and the evidence may point somewhere else.

Output requirements:
- `title`: a memorable two-to-four-word Style Language name, not "Style Report".
- `alignment_summary`: 100-150 words that explain the current-to-desired
  movement directly to the client.
- `current_style_language`: exactly five concise words or short phrases.
- `desired_style_language`: exactly five concise words or short phrases.
- `disconnect`: 100-160 words explaining the meaningful tension and the
  direction that will close it. It must contain interpretation, not a list.
- `style_language_summary`: 60-100 words that make the named Style Language
  feel recognisable and human.
- `style_language_anchors`: exactly three memorable anchor words or phrases.
- `your_action_plan`: exactly three distinct actions with priority, focus,
  action, rationale, and first_step.
- `evidence`: short, concrete observations supporting the interpretation.
- `limitations`: missing or uncertain information that affects confidence.

Language rules:
- Never use internal wording such as "current evidence", "desired evidence",
  "working hypothesis", or "the client" in client-facing fields.
- Do not diagnose personality, psychology, body, identity, age, or lifestyle.
- Do not invent facts or claim that an existing wardrobe contains an item.
  Recommendations may suggest garment categories or styling experiments, but
  clearly present them as options.
- Image URLs without local attachments are metadata only. When local image
  attachments are provided, inspect them and distinguish direct visual
  observations from questionnaire evidence.
- Missing or contradictory information must be acknowledged instead of filled
  with guesses.
- Keep advice practical, specific, non-shaming, and connected to the evidence.
- Do not mention this prompt, the reference portfolios, JSON, or the analysis
  process in the report.
""".strip()


class ActionPlanItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: int = Field(ge=1, le=5)
    focus: str
    action: str
    rationale: str
    first_step: str


class StyleLanguageAnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    alignment_summary: str
    current_style_language: list[str] = Field(min_length=5, max_length=5)
    desired_style_language: list[str] = Field(min_length=5, max_length=5)
    disconnect: str
    style_language_summary: str
    style_language_anchors: list[str] = Field(min_length=3, max_length=3)
    your_action_plan: list[ActionPlanItem] = Field(min_length=3, max_length=3)
    evidence: list[str]
    limitations: list[str]


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
            alignment_summary=(
                f"Your answers point to {current_style} today, while you want to feel "
                f"{style_goal}. This preview does not interpret the gap yet, but it "
                "shows the client-facing shape the real stylist analysis will use."
            ),
            current_style_language=[
                "Practical",
                "Comfort-led",
                "Familiar",
                "Safe",
                "Inconsistent",
            ],
            desired_style_language=[
                "Intentional",
                "Recognisable",
                "Expressive",
                "Confident",
                "Effortless",
            ],
            disconnect=(
                "Your current choices may solve immediate comfort and practicality, "
                "but they do not always create one clear impression. The desired "
                "direction asks for more intention and personality without losing ease. "
                "The real analysis should connect that movement to repeated outfit and "
                "image patterns before recommending a change."
            ),
            style_language_summary=(
                "A useful Style Language turns a vague wish into a direction you can "
                "recognise when getting dressed. This preview uses broad words only; "
                "the real report should make the language specific to your evidence."
            ),
            style_language_anchors=["Ease", "Intention", "Expression"],
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


class CodexCliStyleReportRuntime(StyleReportRuntime):
    """Generate a report through the locally authenticated Codex CLI worker."""

    def __init__(
        self,
        *,
        runner_url: str,
        runner_token: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 600.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.runner_url = runner_url.rstrip("/")
        self.runner_token = runner_token
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def generate(self, request: StyleReportRequest) -> StyleReport:
        headers = {"Content-Type": "application/json"}
        if self.runner_token:
            headers["X-Codex-Runner-Token"] = self.runner_token

        payload = {
            "prompt": _serialize_codex_request(request),
            "model": self.model,
            "output_schema": StyleLanguageAnalysisOutput.model_json_schema(),
            "image_paths": list(request.asset_paths),
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    f"{self.runner_url}/v1/style-reports",
                    headers=headers,
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Codex CLI worker is unreachable: {exc}") from exc

        if response.is_error:
            detail = _response_error_detail(response)
            raise RuntimeError(f"Codex CLI worker returned HTTP {response.status_code}: {detail}")

        try:
            worker_payload = response.json()
            output = StyleLanguageAnalysisOutput.model_validate(worker_payload["report"])
        except (ValueError, KeyError, TypeError) as exc:
            raise RuntimeError(
                "Codex CLI worker returned an invalid style report payload."
            ) from exc

        return StyleReport(
            report_version="codex-cli-v1",
            runtime_type="codex_cli",
            content={
                **output.model_dump(mode="json"),
                "summary": output.alignment_summary,
                "runtime": {
                    "provider": "codex_cli",
                    "model": self.model,
                    "runner_url": self.runner_url,
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


def _serialize_codex_request(request: StyleReportRequest) -> str:
    return (
        f"{STYLE_METHODOLOGIST_INSTRUCTIONS}\n\n"
        "Return only one JSON object that conforms exactly to the provided output schema. "
        "Do not include Markdown fences, commentary, or fields outside that schema.\n\n"
        "Questionnaire evidence:\n"
        f"{_serialize_request(request)}"
    )


def _response_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip()[:500] or "No additional details."
    if isinstance(payload, dict) and isinstance(payload.get("detail"), str):
        return payload["detail"][:500]
    return "No additional details."


class ScaffoldAgentRuntime(AgentRuntime):
    """Placeholder for a future OpenAI Agents SDK Runner integration."""

    async def run(self, request: AgentRunRequest) -> AgentRunResult:
        raise NotImplementedError(
            "Agent execution is intentionally not implemented in the scaffold."
        )
