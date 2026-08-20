from app.agents.canva import ScaffoldCanvaConnector
from app.domain.contracts import AgentRunRequest, ImportRequest, SheetReadRequest


def test_contract_objects_can_be_constructed_without_provider_calls() -> None:
    source = SheetReadRequest(
        spreadsheet_id="synthetic-spreadsheet",
        sheet_name="Form Responses 1",
    )
    request = ImportRequest(source=source, email_header="Email")
    agent_request = AgentRunRequest(
        client_id="synthetic-client",
        submission_id="synthetic-submission",
        context={"source": "fixture"},
    )

    assert request.source.sheet_name == "Form Responses 1"
    assert agent_request.context["source"] == "fixture"


async def test_canva_connector_is_safe_by_default() -> None:
    connector_status = await ScaffoldCanvaConnector().healthcheck()

    assert connector_status.configured is False
