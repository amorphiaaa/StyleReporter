import pytest

from app.agents.runtime import AgentsSdkStyleReportRuntime
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
