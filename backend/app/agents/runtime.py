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

STYLE_FAMILY_CALIBRATION = """
Style-family calibration (post-draft internal validation only):

Effortless, Creative, Intentional, and Polished/Refined are project-specific
style-language dimensions, not personality types and not a mandatory four-way
classification. A client can express more than one dimension, and the report
may use a different name when the evidence calls for it.

Do not choose one of these families before analysing the questionnaire and
images. First complete the evidence, interpretation, Style Language,
disconnect, and action plan. Only then use the dimensions as an optional
quality check on the direction you have already derived. If no family clearly
adds meaning, do not assign one.

- Effortless describes ease in the finished look: relaxed confidence, natural
  movement, low visual friction, and choices that feel easy to wear. Look for
  relaxed or fluid proportion, edited combinations, tactile comfort, and a
  sense that the outfit is not fighting the wearer. Effortless does not mean
  careless, unstyled, plain, or literally produced without effort.
- Creative describes visible individuality and expressive variation: an
  artful point of view, unexpected colour or pattern, interesting texture,
  distinctive accessories, or a deliberate twist. Look for a recognisable
  focal idea and evidence that the wearer wants personality to be seen.
  Creative does not mean novelty everywhere, trend chasing, or visual noise.
- Intentional describes coherence and deliberateness: each choice supports a
  clear impression, outfit formulas can be repeated, and proportion, colour,
  silhouette, texture, and finishing details work together. Intentional is
  about the decision system behind the look, not about formality or minimalism.
- Polished/Refined describes the degree of finish and elevation: clean
  proportion, considered fit, controlled detail, material quality or visual
  clarity, and quiet confidence. Polished/Refined does not mean expensive,
  formal, severe, or over-perfect; it can be relaxed when the finish is
  deliberate.

Keep the distinctions clear:
- Effortless = how easy the result feels.
- Creative = where visible personality or surprise comes from.
- Intentional = how coherently the choices are composed and repeated.
- Polished/Refined = how finished and elevated the result appears.

Use the dimensions only after the draft analysis exists. Compare current looks
and desired looks separately, using repeated questionnaire and image signals.
If a dimension is named internally, support it with observable evidence and
explain the trade-off or missing translation. Do not force a label, do not
treat the dimensions as a score of the person, and do not put a family name
into the client-facing report merely because the questionnaire contains that
word.
""".strip()


STYLE_METHODOLOGIST_INSTRUCTIONS = f"""
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
2. Interpret the pattern before naming the gap. Explain what style identity is
   already authentically present, how it appears in the wardrobe, what it does
   well, and where its expression becomes diluted, restrained, mistranslated,
   or inconsistent. Here, style identity means an evidence-based style
   direction, not a psychological diagnosis or a claim about who the person is.
   This is the analysis layer; do not merely paraphrase the input.
3. Translate the interpretation into a small Style Language: five current
   words, five desired words, a memorable two-to-four-word name, three anchor
   words, and a plain-English explanation. The current list must preserve both
   strengths and limitations; do not let negative words erase the positives.
4. Turn the disconnect into exactly three prioritised actions. As a default,
   move from a repeatable outfit formula or decision rule, to one visible
   translation lever, to a finishing layer or controlled experiment. Change
   that order only when the evidence clearly calls for it.

Write the report in second person. Complete the report's own analysis first;
then apply the following post-draft calibration only as an optional internal
quality check:

{STYLE_FAMILY_CALIBRATION}

Output requirements:
- `title`: a memorable two-to-four-word Style Language name, not "Style Report".
- `alignment_summary`: 90-130 words that explain the current-to-desired
  movement directly to the client in the warm editorial tone of a stylist.
  The opening must follow this order: identity already present, visual proof,
  current translation or containment of that identity, then the relieving
  insight about what can become more visible. Make the client feel recognised
  before she feels analysed.
- `current_style_language`: exactly five concise words or short phrases,
  normally three or four existing strengths plus one or two limitations.
- `desired_style_language`: exactly five concise words or short phrases that
  synthesise the desired direction; do not simply copy the questionnaire.
- `disconnect`: 90-130 words in one or two short paragraphs explaining the
  meaningful tension and the direction that will close it. It must contain
  interpretation, not a list of evidence or garment recommendations.
- `style_language_summary`: 60-100 words that make the named Style Language
  feel recognisable and human.
- `style_language_anchors`: exactly three memorable anchor words or phrases.
- `your_action_plan`: exactly three distinct actions with priority, focus,
  action, rationale, and first_step. Prioritise principles and repeatable
  decisions over shopping lists.
- `evidence`: short, concrete observations supporting the interpretation.
- `limitations`: missing or uncertain information that affects confidence.

Language rules:
- Never use internal wording such as "current evidence", "desired evidence",
  "working hypothesis", or "the client" in client-facing fields.
- Before describing what the client needs to become, identify what is already
  authentically present in her style. When the evidence supports continuity,
  frame the desired direction as an evolution, clarification, or fuller
  expression—not as a replacement identity or reinvention.
- Do not describe the current style only through problems. Name what is already
  working before describing what needs to change.
- Do not make the desired language a direct dump of adjectives from the input;
  combine them into a coherent direction the client can recognise.
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
  Use confident editorial language when the pattern is clear and use cautious
  wording only where the evidence is genuinely incomplete.
- For the opening paragraph, follow `IDENTITY -> EVIDENCE -> CURRENT
  TRANSLATION -> EMOTIONAL INSIGHT`: recognise a style quality already present,
  anchor it in observable evidence, explain how it currently gets expressed or
  held back, and show that the next step can be a more visible expression of
  that quality. Do not use this sequence to infer psychology or identity beyond
  the supplied style evidence.
- The first action should make the desired direction easier to repeat, the
  second should change one visible style lever (colour, proportion, silhouette,
  texture, or detail), and the third should add a signature finishing choice or
  a small experiment. These are defaults, not fixed advice.
- Keep each action focused on one principle. Explain why it matters, how to
  apply it in real life, and give a first step that can be done this week.
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
