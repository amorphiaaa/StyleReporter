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
