import json
from pathlib import Path

import pytest

from app.domain.contracts import ImportRequest, SheetReadRequest, SheetRow
from app.integrations.google_sheets import FixtureGoogleSheetsSource
from app.services.questionnaire_importer import QuestionnaireImportService
from tests.fakes import InMemoryClientRepository, InMemorySubmissionRepository

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_questionnaire_rows.json"


def load_fixture_rows() -> list[SheetRow]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return [SheetRow(row_number=item["row_number"], values=item["values"]) for item in payload]


def build_importer(
    rows: list[SheetRow],
) -> tuple[QuestionnaireImportService, InMemoryClientRepository, InMemorySubmissionRepository]:
    clients = InMemoryClientRepository()
    submissions = InMemorySubmissionRepository()
    source = FixtureGoogleSheetsSource(rows)
    importer = QuestionnaireImportService(source, clients, submissions)
    return importer, clients, submissions


def import_request() -> ImportRequest:
    return ImportRequest(
        source=SheetReadRequest(
            spreadsheet_id="synthetic-spreadsheet",
            sheet_name="Form Responses 1",
        ),
        email_header="Email",
        display_name_header="Name",
        questionnaire_version="fixture-v1",
    )


@pytest.mark.asyncio
async def test_importer_normalizes_email_and_preserves_raw_payload() -> None:
    importer, clients, submissions = build_importer(load_fixture_rows())

    result = await importer.import_rows(import_request())

    assert result.rows_seen == 4
    assert result.created_clients == 2
    assert result.updated_clients == 1
    assert result.created_submissions == 3
    assert result.rejected_rows == 1
    assert result.skipped_duplicates == 0
    assert result.errors[0].code == "invalid_email"
    assert set(clients.items) == {
        "synthetic.client@example.test",
        "second.client@example.test",
    }

    first_submission = submissions.items[("synthetic-spreadsheet", "Form Responses 1", 2)]
    assert first_submission.raw_payload["Email"] == "synthetic.client@example.test"
    assert first_submission.source_row_hash
    assert first_submission.questionnaire_version == "fixture-v1"


@pytest.mark.asyncio
async def test_importer_skips_duplicate_source_rows() -> None:
    row = load_fixture_rows()[0]
    importer, _, submissions = build_importer([row, row])

    result = await importer.import_rows(import_request())

    assert result.rows_seen == 2
    assert result.skipped_duplicates == 1
    assert result.created_submissions == 1
    assert len(submissions.items) == 1


@pytest.mark.asyncio
async def test_importer_is_idempotent_for_rows_already_in_repository() -> None:
    importer, clients, submissions = build_importer([load_fixture_rows()[0]])

    first_result = await importer.import_rows(import_request())
    second_result = await importer.import_rows(import_request())

    assert first_result.created_clients == 1
    assert first_result.created_submissions == 1
    assert second_result.created_clients == 0
    assert second_result.updated_clients == 0
    assert second_result.created_submissions == 0
    assert second_result.skipped_duplicates == 1
    assert len(clients.items) == 1
    assert len(submissions.items) == 1


@pytest.mark.asyncio
async def test_fixture_source_rejects_another_sheet() -> None:
    source = FixtureGoogleSheetsSource(load_fixture_rows())
    request = SheetReadRequest(
        spreadsheet_id="synthetic-spreadsheet",
        sheet_name="Another Sheet",
    )

    with pytest.raises(ValueError, match="sheet name"):
        await source.read_rows(request)
