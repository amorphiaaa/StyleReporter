import pytest
from pydantic import ValidationError

from app.api.schemas.imports import ManualImportRequest


def test_manual_import_request_maps_inline_rows_to_domain() -> None:
    payload = ManualImportRequest(
        spreadsheet_id="synthetic-spreadsheet",
        sheet_name="Form Responses 1",
        email_header="Email",
        rows=[
            {
                "row_number": 2,
                "values": {"Email": "synthetic.client@example.test"},
            }
        ],
    )

    request = payload.to_domain(import_id="f71fa28b-e681-4fb9-9252-53078bd9ecf5")

    assert request.source.spreadsheet_id == "synthetic-spreadsheet"
    assert request.import_id == "f71fa28b-e681-4fb9-9252-53078bd9ecf5"
    assert payload.rows_to_domain()[0].values["Email"] == "synthetic.client@example.test"


def test_manual_import_request_requires_at_least_one_row() -> None:
    with pytest.raises(ValidationError):
        ManualImportRequest(
            spreadsheet_id="synthetic-spreadsheet",
            sheet_name="Form Responses 1",
            email_header="Email",
            rows=[],
        )


def test_manual_import_request_can_refresh_existing_rows() -> None:
    payload = ManualImportRequest(
        spreadsheet_id="synthetic-spreadsheet",
        sheet_name="Form Responses 1",
        email_header="Email",
        refresh_existing=True,
        rows=[
            {
                "row_number": 2,
                "values": {"Email": "synthetic.client@example.test"},
            }
        ],
    )

    request = payload.to_domain(import_id="f71fa28b-e681-4fb9-9252-53078bd9ecf5")

    assert request.refresh_existing is True
