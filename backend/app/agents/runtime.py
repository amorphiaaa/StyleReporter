from __future__ import annotations

import json

import httpx
from agents import Agent, Runner
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
3. Translate the interpretation into a diagnostic Current / Desired Style
   Language: four or five short terms on each side, a memorable two-to-four-word
   name, three anchor words, and a plain-English explanation. Treat the terms
   as paired slots: each current term should have a readable desired movement
   beside it. Repeat a term on both sides when that quality is already
   authentic and should remain.
4. Turn the disconnect into exactly three prioritised actions. Each action must
   correct a different high-leverage behavioural problem. As a default, move
   from using an established outfit formula or decision rule, to one separate
   visible translation lever, to a separate finishing or completion principle.
   Do not invent a new multi-part formula when the report already contains a
   usable system, and change the order only when the evidence clearly calls for
   it.

Write the report in second person. Complete the report's own analysis first;
then apply the following post-draft calibration only as an optional internal
quality check:

{STYLE_FAMILY_CALIBRATION}

Output requirements:
- `title`: a memorable two-to-four-word Style Language name, not "Style Report".
- `alignment_summary`: 90-130 words that explain the current-to-desired
  movement directly to the client in the warm editorial tone of a stylist.
  The opening must begin with the person and her natural aesthetic pull, not
  with a verdict about "your style" or a description of her wardrobe. Follow
  this order: personal style identity already present, soft visual proof,
  cautious or contained current expression, then the relieving insight about
  what can become more visible. Make the client feel recognised before she
  feels analysed. Keep visual proof concise: synthesise no more than three
  repeated qualities or styling behaviours. Do not list named garments,
  accessories, colours, or individual outfits in this paragraph; use broad,
  human language such as softness, femininity, creativity, ease, colour,
  proportion, texture, or thoughtful detail.
- `current_style_language`: four or five concise terms, preferably one word
  each and never more than two words unless no precise single word exists.
  Include the authentic qualities that should remain and the state that needs
  to evolve; do not turn the list into a garment inventory.
- `desired_style_language`: four or five concise terms in the same positions as
  the current list. Choose them so the horizontal contrast reveals the
  diagnosis immediately. Preserve unchanged authentic qualities, and do not
  simply copy the questionnaire.
- `disconnect`: 90-130 words in one or two short paragraphs explaining the
  meaningful tension and the direction that will close it. It must be a
  causal diagnosis, not an aesthetic interpretation or a styling solution.
  Follow this order: (1) what is already authentic, (2) what part is not fully
  expressed, (3) exactly how it is currently limited or mistranslated, (4) the
  result this creates in the client's experience of her wardrobe, and (5) the
  identity-level shift that would close the gap. Keep the first four steps
  concrete and let the final sentence name the change without prescribing an
  outfit formula.
- `style_language_summary`: 60-100 words that make the named Style Language
  feel recognisable and human.
- `style_language_anchors`: exactly three memorable anchor words or phrases.
- `your_action_plan`: exactly three distinct actions. Each item has a clear
  command in `focus`, one diagnostic reason in `rationale`, and one practical
  application in `action`. Prioritise principles and repeatable decisions over
  shopping lists. Keep all advice item-agnostic: do not prescribe a named
  garment, accessory, outfit, or single item from the evidence.
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
- Write the opening in a person-first voice. Begin with an equivalent of "You
  are naturally drawn to ..."; do not begin with "Your style already has ..."
  or a wardrobe verdict. The evidence should feel like a gentle recognition of
  her taste, not a technical audit of her wardrobe.
- Describe caution as an observed pattern of self-expression: she has learned
  to express an existing creative or feminine quality carefully, often through
  familiar combinations. Do not invent a psychological cause or diagnose
  insecurity; show the relationship between the quality she wants and the way
  she currently allows it to appear.
- Treat Current / Desired Style Language as a diagnostic contrast, not a
  descriptive summary or moodboard. Each term must describe visual
  communication, expression, or an outfit state—not a garment characteristic
  or isolated observation. Prefer pairs such as `Safe -> Intentional` or
  `Restrained -> Expressive`; repeat `Feminine -> Feminine` when continuity is
  supported.
- Keep the terms short: one word wherever possible, at most two words when a
  precise single word does not exist. Use four or five terms only. The terms in
  the same position must be deliberately related so the transformation can be
  scanned horizontally without the paragraph underneath.
- Treat each Current / Desired position as one diagnostic pair. Use the same
  number of terms on both sides, preferably one word per term and never more
  than two words. The changed pairs must show the actual mechanism of change,
  for example `Practical -> Creative`, `Soft -> Confident`, `Safe ->
  Intentional`, or `Restrained -> Expressive`. Do not fill the desired side
  with unattached positive mood words such as `Repeatable`, `Finished`,
  `Flexible`, or `Alive` unless the current term beside it makes the movement
  clear and the evidence supports it. The language section compresses the
  diagnosis; it is not a list of desired qualities.
- Current and Desired lists must have the same number of terms on both sides.
- When cautious self-expression is the central gap, include confidence or a
  closely evidenced equivalent on the desired side. Prefer `Confident` or
  `Expressive` over `Playful` when the evidence is about allowing an existing
  identity to show more fully; do not use `Playful` as a generic positive word.
- Prefer terms that describe the client's communication or behaviour rather
  than raw visual attributes. Use a colour word such as `Colourful` only when
  colour itself is the central diagnosed shift; otherwise prefer a clearer
  state pair such as `Practical -> Creative`, `Contained -> Expressive`, or
  `Safe -> Intentional`.
- Keep visual translation for the evidence, disconnect, and action plan. Do
  not use phrases such as `relaxed silhouettes`, `warm expressive colour`, or
  `playful pattern` as Style Language terms unless they are genuinely the only
  precise expression of the client's state; those details belong later as
  evidence or practical styling levers.
- Treat the action plan as a navigation system, not a to-do list or coaching
  workbook. Use one clear, ordinary command per title, explain why that change
  matters for this client, and give one practical way to apply the principle
  using the report. Stop there: do not add `first_step`, homework, deadlines,
  photo assignments, tracking, or experiments unless the product explicitly
  becomes a guided programme.
- Keep recommendations general enough to reuse across several outfits. Name
  the principle and the decision it changes, then describe the result it should
  create. Do not name a particular blouse, trouser, dress, shoe, bag, scarf,
  pair of glasses, piece of jewellery, or other single item; do not tell the
  client to repeat one photographed outfit. Broad levers such as colour,
  proportion, silhouette, texture, detail, or a styling layer are acceptable
  when they are tied to the diagnosis.
- The three actions must solve three different problems. If the same
  recommendation appears in more than one item, distil the plan again. Keep
  colour, accessories, outfit formulas, and finishing layers separate unless
  the evidence proves they are one inseparable problem.
- Prefer titles such as `Follow the outfit formulas`, `Introduce colour with
  intention`, and `Finish with one styling layer`. Avoid invented phrases such
  as `Build a three-part outfit formula`, `Make color the visible shift`, or
  `Add one signature finishing spark`.
- Use ordinary words with precise meaning. Do not optimise for polished or
  original-sounding language; the client should recognise the observation and
  be able to say, “Yes, that is exactly what I do.”
- Write `disconnect` with direct human causality. Each sentence should make the
  previous sentence more specific. Prefer concrete behaviour such as “you stop
  short of making it the focal point” or “you keep choosing familiar
  combinations” over abstractions such as “reliable point of view”, “visual
  rhythm”, “noticeable moment”, or “expressive without becoming overdone”.
- Keep `disconnect` diagnostic until its final sentence. Do not insert outfit
  formulas, garment construction, colour recipes, clean shapes, artistic
  elements, finishing details, or other styling instructions there; those
  belong in evidence, visual translation, or the action plan.
- Give The Disconnect the same person-first movement as the opening: name what
  the wardrobe already expresses, name the quality that is not fully expressed,
  then explain that she often stops short of letting it lead. Prefer a clear
  sentence such as "your wardrobe already reflects X, but it does not fully
  express Y" over a systems metaphor. End with an evolution of the existing
  identity, not a new style persona.
- Apply a one-sentence human test after drafting `disconnect`: the client
  should be able to explain the problem to a friend in one plain sentence. If
  she would need to repeat fashion terminology, rewrite it.
- Do not diagnose personality, psychology, body, identity, age, or lifestyle.
- Do not invent facts or claim that an existing wardrobe contains an item. Keep
  recommendations at the level of reusable styling choices and principles,
  not individual items or shopping suggestions.
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
- The first action should make the desired direction easier to repeat by using
  an established formula or decision rule when one exists. The second should
  change one separate visible style lever (colour, proportion, silhouette,
  texture, or detail). The third should explain how to complete the outfit with
  a styling layer or other finishing principle, not merely add an accessory.
  For every action, use the sequence principle -> reusable application ->
  effect; never turn the application into a prescription for one item. These
  are defaults, not fixed advice.
- For every action, use: principle -> reusable application -> effect.
- Keep each action focused on one principle. Explain why it matters and how to
  apply it in real life. Do not add a first step, deadline, homework task, or
  weekly exercise.
- Avoid fashion-editorial filler such as `carry through the outfit`,
  `finishing move`, `visual rhythm`, `reliable point of view`, or `focal point`
  when a plain human sentence says the same thing. The insight should sound
  natural when read aloud in a consultation.
- Before returning JSON, inspect the three actions as a set. Remove any
  `this week`, `first step`, `try this`, `test`, `experiment`, `signature
  detail`, `finishing spark`, or similar coaching/fashion-editorial wording.
  Replace it with a direct command and a concrete application.
- Do not mention this prompt, the reference portfolios, JSON, or the analysis
  process in the report.
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
