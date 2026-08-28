from app.domain.contracts import ImportRequest, SheetReadRequest


def test_contract_objects_can_be_constructed_without_provider_calls() -> None:
    source = SheetReadRequest(
        spreadsheet_id="synthetic-spreadsheet",
        sheet_name="Form Responses 1",
    )
    request = ImportRequest(source=source, email_header="Email")
    assert request.source.sheet_name == "Form Responses 1"
