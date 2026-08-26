import json

import httpx
import pytest
from pydantic import ValidationError

from app.agents.canva_portfolio import (
    CanvaPortfolioOutput,
    CodexCliCanvaPortfolioRuntime,
)
from app.agents.runtime import (
    STYLE_FAMILY_CALIBRATION,
    STYLE_METHODOLOGIST_INSTRUCTIONS,
    AgentsSdkStyleReportRuntime,
    CodexCliStyleReportRuntime,
    StyleLanguageAnalysisOutput,
)
from app.agents.style_methodologist import StubStyleReportRuntime
from app.domain.contracts import CanvaPortfolioRequest, StyleReportRequest


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
    assert "same number of terms on both sides" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "Practical -> Creative" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "unattached positive mood words" in STYLE_METHODOLOGIST_INSTRUCTIONS


def test_disconnect_prompt_requires_causal_human_diagnosis() -> None:
    assert "causal diagnosis, not an aesthetic interpretation" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "what is already authentic" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "what part is not fully" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "identity-level shift" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "direct human causality" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "reliable point of view" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "Do not insert outfit" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "one-sentence human test" in STYLE_METHODOLOGIST_INSTRUCTIONS


def test_action_plan_prompt_prioritises_principles_over_homework() -> None:
    assert "navigation system, not a to-do list" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "three different problems" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "do not add `first_step`" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "Follow the outfit formulas" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "signature finishing spark" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "styling layer or other finishing principle" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "Keep all advice item-agnostic" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "principle -> reusable application -> effect" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert "Do not name a particular blouse" in STYLE_METHODOLOGIST_INSTRUCTIONS
    assert (
        "Before returning JSON, inspect the three actions as a set"
        in STYLE_METHODOLOGIST_INSTRUCTIONS
    )
    assert "give a first step that can be done this week" not in STYLE_METHODOLOGIST_INSTRUCTIONS


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
                },
                {
                    "priority": 2,
                    "focus": "Review repetition",
                    "action": "List repeated choices.",
                    "rationale": "Repetition shows current language.",
                },
                {
                    "priority": 3,
                    "focus": "Record the result",
                    "action": "Note what changed.",
                    "rationale": "Notes make the experiment useful.",
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


async def test_canva_runtime_validates_candidate_payload_without_provider_calls() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/canva/design-candidates"
        payload = json.loads(request.read())
        assert "StyleReporter" in payload["prompt"]
        return httpx.Response(
            200,
            json={
                "result": {
                    "status": "completed",
                    "candidates": [
                        {
                            "candidate_id": "candidate-1",
                            "job_id": "job-1",
                            "title": "Editorial Style Report",
                            "design_url": "https://canva.example/design-1",
                            "thumbnail_url": "https://canva.example/thumb-1",
                        }
                    ],
                    "note": "Synthetic candidate response.",
                }
            },
            request=request,
        )

    runtime = CodexCliCanvaPortfolioRuntime(
        runner_url="http://codex-worker:8787/",
        transport=httpx.MockTransport(handler),
    )
    result = await runtime.generate_candidates(
        CanvaPortfolioRequest(
            client_id="client-1",
            report_run_id="report-1",
            client_name="Synthetic Client",
            report={"title": "Synthetic Style Language"},
            questionnaire_context={"normalized_answers": {}},
            asset_paths=("clients/client-1/submission-1/01.jpg",),
        )
    )

    assert result.status == "completed"
    assert result.note == "Synthetic candidate response."
    assert result.candidates[0].candidate_id == "candidate-1"
    assert result.candidates[0].design_url == "https://canva.example/design-1"


def test_canva_output_schema_is_strict() -> None:
    schema = CanvaPortfolioOutput.model_json_schema()

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    candidate_schema = schema["$defs"]["CanvaDesignCandidateOutput"]
    assert candidate_schema["additionalProperties"] is False
    assert set(candidate_schema["required"]) == set(candidate_schema["properties"])


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
    assert set(action_schema["required"]) == {"priority", "focus", "action", "rationale"}
    assert "first_step" not in action_schema["properties"]


def test_codex_output_rejects_unpaired_or_overlong_style_terms() -> None:
    base = {
        "title": "Synthetic Style",
        "alignment_summary": "A useful summary.",
        "current_style_language": ["Feminine", "Safe", "Soft", "Practical"],
        "desired_style_language": [
            "Feminine",
            "Intentional",
            "Confident",
            "Creative",
        ],
        "disconnect": "A clear causal explanation.",
        "style_language_summary": "A clear direction.",
        "style_language_anchors": ["Ease", "Clarity", "Expression"],
        "your_action_plan": [
            {
                "priority": 1,
                "focus": "Use a repeatable principle",
                "action": "Apply the report's decision rule.",
                "rationale": "It reduces uncertainty.",
            },
            {
                "priority": 2,
                "focus": "Change one visual lever",
                "action": "Change one visible quality.",
                "rationale": "It makes the shift clearer.",
            },
            {
                "priority": 3,
                "focus": "Complete the look",
                "action": "Use a finishing principle.",
                "rationale": "It makes the result feel coherent.",
            },
        ],
        "evidence": ["Synthetic evidence."],
        "limitations": [],
    }

    unpaired = {**base, "desired_style_language": ["Feminine"] * 5}
    with pytest.raises(ValidationError, match="same number of terms"):
        StyleLanguageAnalysisOutput.model_validate(unpaired)

    overlong = {
        **base,
        "current_style_language": [
            "Too many words here",
            "Safe",
            "Soft",
            "Practical",
        ],
    }
    with pytest.raises(ValidationError, match="at most two words"):
        StyleLanguageAnalysisOutput.model_validate(overlong)
