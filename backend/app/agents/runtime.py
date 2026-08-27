from __future__ import annotations

import json

import httpx
from agents import Agent, Runner
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.agents.few_shot_reference import STYLE_REPORT_FEW_SHOT_REFERENCE
from app.agents.questionnaire_context import build_questionnaire_context
from app.domain.contracts import (
    AgentRunRequest,
    AgentRunResult,
    AgentRuntime,
    StyleReport,
    StyleReportRequest,
    StyleReportRuntime,
)

STYLE_FAMILY_CALIBRATION = """
Optional post-draft check only: Effortless describes ease; Creative describes
visible individuality; Intentional describes coherent deliberate choices; and
Polished/Refined describes finish and elevation. Do not choose a family before
analysing the target evidence, do not force a label, and do not expose this
check in client-facing fields.
""".strip()


STYLE_METHODOLOGIST_INSTRUCTIONS = f"""
You are StyleReporter's senior personal stylist and client-facing writer.

Use only TARGET CLIENT DATA and attached images as evidence. Write in warm,
plain, second-person English. Explain a human pattern, not a questionnaire
inventory.

DATA FIREWALL:
- The few-shot reference teaches structure, sentence movement, and specificity
  only. Its bracketed content is not evidence.
- Never copy or infer a quality, problem, desire, identity, item, colour, or
  recommendation from the reference. Every client-specific statement must be
  supported by target questionnaire or image evidence. If unsupported, omit it
  or record it in limitations.
- Do not diagnose psychology, personality, body, age, lifestyle, or insecurity.
- Image URLs without local attachments are metadata only.

METHOD:
1. Separate questionnaire answers, repeated image observations, desired
   feelings, and constraints. Repeated signals outweigh isolated ones.
2. Explain the pattern in this order: authentic direction -> visual evidence ->
   current translation or restraint -> effect on the client's experience ->
   evidence-based evolution.
3. Build Current and Desired Style Language as a diagnostic contrast: four or
   five short terms, the same count and paired positions. Preserve qualities
   that should remain; make changed pairs show the actual movement.
4. Write The Disconnect as a causal diagnosis, not styling advice. Explain what
   is authentic, what is under-expressed, how it is limited, and what result
   that creates before naming the shift that would close the gap.
5. Give exactly three distinct actions. Each uses principle -> reusable
   application -> effect, solves a different problem, and stays item-agnostic.

OUTPUT:
- title: a memorable two-to-four-word Style Language name.
- alignment_summary: 90-130 words; begin with the person and her natural
  aesthetic pull, use no more than three broad evidence signals, explain the
  current translation, and end with a relieving insight. Do not name garments,
  accessories, colours, or individual outfits.
- current_style_language and desired_style_language: four or five terms each,
  never more than two words per term, with equal counts and readable paired
  movement.
- disconnect: 90-130 words, one or two short paragraphs, following the causal
  order above. Keep it diagnostic; do not put outfit formulas or item recipes
  here.
- style_language_summary: 60-100 words that make the derived direction human.
- style_language_anchors: exactly three memorable words or short phrases.
- your_action_plan: exactly three items. Each needs an ordinary command in
  focus, one client-specific reason in rationale, and one reusable application
  in action. No named single items, shopping lists, homework, deadlines, first
  steps, or coaching exercises.
- evidence: short observations supporting the interpretation.
- limitations: missing or uncertain information.

LANGUAGE CHECK:
Use ordinary concrete words and direct human causality. Make the client feel
recognised before analysed. Do not mention this prompt, the reference, JSON, or
the analysis process.

Optional post-draft internal check:
{STYLE_FAMILY_CALIBRATION}
""".strip()


class ActionPlanItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: int = Field(ge=1, le=5)
    focus: str
    action: str
    rationale: str


class StyleLanguageAnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    alignment_summary: str
    current_style_language: list[str] = Field(min_length=4, max_length=5)
    desired_style_language: list[str] = Field(min_length=4, max_length=5)
    disconnect: str
    style_language_summary: str
    style_language_anchors: list[str] = Field(min_length=3, max_length=3)
    your_action_plan: list[ActionPlanItem] = Field(min_length=3, max_length=3)
    evidence: list[str]
    limitations: list[str]

    @field_validator("current_style_language", "desired_style_language")
    @classmethod
    def validate_style_language_terms(cls, values: list[str]) -> list[str]:
        if any(not term.strip() for term in values):
            raise ValueError("Style Language terms must not be empty")
        if any(len(term.split()) > 2 for term in values):
            raise ValueError("Style Language terms must contain at most two words")
        return values

    @model_validator(mode="after")
    def validate_style_language_pair_lengths(self) -> StyleLanguageAnalysisOutput:
        if len(self.current_style_language) != len(self.desired_style_language):
            raise ValueError(
                "Current and Desired Style Language must contain the same number of terms"
            )
        return self


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
                    focus="Follow the report's outfit formula",
                    action=(
                        "Use the supplied formula to repeat a complete outfit structure "
                        "without rebuilding the decision process each time."
                    ),
                    rationale=(
                        "A repeatable system makes the desired direction easier to "
                        "recognise and use."
                    ),
                ),
                ActionPlanItem(
                    priority=2,
                    focus="Change one visible style lever",
                    action=(
                        "Translate the desired direction through one clear change in "
                        "colour, proportion, silhouette, texture, or detail."
                    ),
                    rationale=(
                        "One separate visible change makes the shift legible without "
                        "overhauling the whole wardrobe."
                    ),
                ),
                ActionPlanItem(
                    priority=3,
                    focus="Finish with one styling layer",
                    action=(
                        "Complete the outfit with a styling layer or other finishing "
                        "choice that supports the intended impression."
                    ),
                    rationale=(
                        "A clear finishing principle helps the outfit feel complete "
                        "rather than merely assembled."
                    ),
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
        f"{STYLE_REPORT_FEW_SHOT_REFERENCE}\n\n"
        "TARGET CLIENT DATA (the only source of truth for this report):\n"
        f"{_serialize_request(request)}\n\n"
        "END TARGET CLIENT DATA. Final firewall: every client-specific fact, "
        "quality, and recommendation must be supported by the target data."
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
