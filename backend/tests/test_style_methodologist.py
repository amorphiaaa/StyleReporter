import httpx
import pytest

from app.agents.runtime import (
    AgentsSdkStyleReportRuntime,
    CodexCliStyleReportRuntime,
    StyleLanguageAnalysisOutput,
)
from app.agents.style_methodologist import StubStyleReportRuntime
from app.domain.contracts import StyleReportRequest


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
    assert "elegant but repetitive" in result.content["current_style_language"]
    assert "More like myself" in result.content["desired_style_language"]
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
            "current_style_language": "Current signals are clear.",
            "desired_style_language": "Desired signals are expressive.",
            "disconnect": "The target needs one visible experiment.",
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
    action_schema = schema["$defs"]["ActionPlanItem"]
    assert action_schema["additionalProperties"] is False
    assert set(action_schema["required"]) == set(action_schema["properties"])
