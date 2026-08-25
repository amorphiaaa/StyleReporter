import httpx
import pytest

from app.agents.runtime import (
    STYLE_FAMILY_CALIBRATION,
    STYLE_METHODOLOGIST_INSTRUCTIONS,
    AgentsSdkStyleReportRuntime,
    CodexCliStyleReportRuntime,
    StyleLanguageAnalysisOutput,
)
from app.agents.style_methodologist import StubStyleReportRuntime
from app.domain.contracts import StyleReportRequest


def test_style_family_calibration_defines_dimensions_without_forcing_labels() -> None:
    assert "post-draft internal validation only" in STYLE_FAMILY_CALIBRATION
    assert "Do not choose one of these families before analysing" in STYLE_FAMILY_CALIBRATION
    assert "not personality types" in STYLE_FAMILY_CALIBRATION
    assert "Effortless = how easy the result feels" in STYLE_FAMILY_CALIBRATION
    assert "Creative = where visible personality or surprise comes from" in STYLE_FAMILY_CALIBRATION
    assert (
        "Intentional = how coherently the choices are composed and repeated"
        in STYLE_FAMILY_CALIBRATION
    )
    assert (
        "Polished/Refined = how finished and elevated the result appears"
        in STYLE_FAMILY_CALIBRATION
    )
    assert "Do not force a label" in STYLE_FAMILY_CALIBRATION
    assert STYLE_FAMILY_CALIBRATION in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "post-draft calibration only as an optional internal" in STYLE_METHODOLOGIST_INSTRUCTIONS


def test_methodologist_prompt_preserves_continuity_of_style_identity() -> None:
    assert "what style identity is" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "already authentically present" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "identity already present, visual proof" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "evolution, clarification, or fuller" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert (
        "Make the client feel recognised" in STYLE_METHODOLOGIST_INSTRUCTIONS
    )
    assert (
        "before she feels analysed" in STYLE_METHODOLOGIST_INSTRUCTIONS
    )
    assert (
        "Do not use this sequence to infer psychology or identity"
        in STYLE_METHODOLOGIST_INSTRUCTIONS
    )


def test_style_language_prompt_requires_diagnostic_contrasts() -> None:
    assert "diagnostic Current / Desired Style" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "four or five concise terms" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "same positions as" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert (
        "diagnostic contrast, not a"
        in STYLE_METHODOLOGIST_INSTRUCTIONS
    )
    assert "descriptive summary or moodboard" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "Safe -> Intentional" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "relaxed silhouettes" in STYLE_METHODOLOGIST_INSTRUCTIONS


async def test_stub_runtime_returns_deterministic_scaffold_report() -> None:
    result = await StubStyleReportRuntime().generate(
        StyleReportRequest(
            client_id="client-1",
            submission_id="submission-1",
            raw_payload={"Email": "client@example.test", "Style goal": "More color"},
        )
    )

    assert result.runtime_type == "stub"
    assert result.report_version == "stub-v1"
    assert result.content["evidence"] == {
        "source_submission_id": "submission-1",
        "answered_fields": ["Email", "Style goal"],
    }


async def test_agents_sdk_runtime_dry_run_constructs_agent_without_model_call() -> None:
    runtime = AgentsSdkStyleReportRuntime(model="synthetic-model")

    result = await runtime.generate(
        StyleReportRequest(
            client_id="client-1",
            submission_id="submission-1",
            raw_payload={"Email": "client@example.test"},
        )
    )

    assert runtime.agent.name == "Style methodologist"
    assert result.runtime_type == "agents_sdk_dry_run"
    assert result.report_version == "agents-sdk-contract-v1"
    assert result.content["runtime"] == {
        "agent_name": "Style methodologist",
        "model": "synthetic-model",
        "dry_run": True,
    }


async def test_agents_sdk_dry_run_contains_style_language_analysis_sections() -> None:
    runtime = AgentsSdkStyleReportRuntime(model="synthetic-model")

    result = await runtime.generate(
        StyleReportRequest(
            client_id="client-1",
            submission_id="submission-1",
            questionnaire_version="fixture-v1",
            raw_payload={
                "Email": "client@example.test",
                "Name": "Synthetic Client",
                "How would you describe your style today?": "elegant but repetitive",
                "What would you love your style to help you feel?": "More like myself",
                "Visual world": "B",
            },
        )
    )

    assert result.content["title"] == "Style Language analysis preview"
    assert result.content["alignment_summary"]
    assert "Practical" in result.content["current_style_language"]
    assert "Intentional" in result.content["desired_style_language"]
    assert len(result.content["style_language_anchors"]) == 3
    assert result.content["disconnect"]
    assert len(result.content["your_action_plan"]) == 3
    assert "Missing questionnaire field: style_discomfort" in result.content["limitations"]


async def test_agents_sdk_runtime_requires_key_when_not_dry_run() -> None:
    runtime = AgentsSdkStyleReportRuntime(dry_run=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        await runtime.generate(
            StyleReportRequest(
                client_id="client-1",
                submission_id="submission-1",
                raw_payload={"Email": "client@example.test"},
            )
        )


async def test_codex_cli_runtime_validates_worker_output_without_openai_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/style-reports"
        assert b"clients/client-1/submission-1/01.jpg" in request.read()
        payload = {
            "title": "Synthetic Codex report",
            "alignment_summary": "The current and desired directions are clear.",
            "current_style_language": [
                "Practical",
                "Safe",
                "Casual",
                "Familiar",
                "Inconsistent",
            ],
            "desired_style_language": [
                "Intentional",
                "Expressive",
                "Modern",
                "Confident",
                "Recognisable",
            ],
            "disconnect": "The target needs one visible experiment.",
            "style_language_summary": "A clear direction makes everyday choices easier.",
            "style_language_anchors": ["Ease", "Intention", "Expression"],
            "your_action_plan": [
                {
                    "priority": 1,
                    "focus": "Test one signal",
                    "action": "Change one styling decision.",
                    "rationale": "A small test creates evidence.",
                    "first_step": "Choose one outfit.",
                },
                {
                    "priority": 2,
                    "focus": "Review repetition",
                    "action": "List repeated choices.",
                    "rationale": "Repetition shows current language.",
                    "first_step": "Review three outfits.",
                },
                {
                    "priority": 3,
                    "focus": "Record the result",
                    "action": "Note what changed.",
                    "rationale": "Notes make the experiment useful.",
                    "first_step": "Write two observations.",
                },
            ],
            "evidence": ["Synthetic questionnaire evidence."],
            "limitations": [],
        }
        return httpx.Response(200, json={"report": payload}, request=request)

    runtime = CodexCliStyleReportRuntime(
        runner_url="http://codex-worker:8787/",
        model=None,
        transport=httpx.MockTransport(handler),
    )

    result = await runtime.generate(
        StyleReportRequest(
            client_id="client-1",
            submission_id="submission-1",
            raw_payload={"Email": "client@example.test"},
            asset_paths=("clients/client-1/submission-1/01.jpg",),
        )
    )

    assert result.runtime_type == "codex_cli"
    assert result.report_version == "codex-cli-v1"
    assert result.content["title"] == "Synthetic Codex report"
    assert result.content["runtime"] == {
        "provider": "codex_cli",
        "model": None,
        "runner_url": "http://codex-worker:8787",
    }


def test_codex_output_schema_is_strict_for_every_object() -> None:
    schema = StyleLanguageAnalysisOutput.model_json_schema()

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["properties"]["current_style_language"]["minItems"] == 4
    assert schema["properties"]["current_style_language"]["maxItems"] == 5
    assert schema["properties"]["desired_style_language"]["minItems"] == 4
    assert schema["properties"]["desired_style_language"]["maxItems"] == 5
    action_schema = schema["$defs"]["ActionPlanItem"]
    assert action_schema["additionalProperties"] is False
    assert set(action_schema["required"]) == set(action_schema["properties"])
