import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.contracts import (
    ClientRecord,
    ImportRequest,
    QuestionnaireSubmission,
    SheetReadRequest,
    SheetRow,
)
from app.domain.questionnaire import extract_questionnaire_assets
from app.integrations.google_sheets import FixtureGoogleSheetsSource
from app.services.asset_workspace import LocalAssetWorkspace
from app.services.questionnaire_importer import QuestionnaireImportService
from tests.fakes import InMemoryClientRepository, InMemorySubmissionRepository


def test_image_assets_follow_the_versioned_questionnaire_mapping() -> None:
    payload = {
        "Email": "synthetic.client@example.test",
        "Feels Like Me images": "https://example.test/feels-1.jpg,\nhttps://example.test/feels-2.jpg",
        "Not Me image": "https://example.test/not-me.jpg",
        "Inspiration images": "https://example.test/inspiration-1.jpg, https://example.test/inspiration-2.jpg",
    }

    assets = extract_questionnaire_assets(payload, version="fixture-v1")

    assert [(asset.field_key, asset.ordinal) for asset in assets] == [
        ("feels_like_me_images", 1),
        ("feels_like_me_images", 2),
        ("not_me_image", 1),
        ("inspiration_images", 1),
        ("inspiration_images", 2),
    ]


@pytest.mark.asyncio
async def test_local_workspace_writes_questionnaire_and_manifest(tmp_path: Path) -> None:
    client = ClientRecord(
        id="client-123",
        email_normalized="synthetic.client@example.test",
        display_name="Synthetic Client",
    )
    submission = QuestionnaireSubmission(
        id="submission-456",
        client_id=client.id,
        source_type="google_sheets",
        source_spreadsheet_id="synthetic-spreadsheet",
        source_sheet_name="Form Responses 1",
        source_row_number=2,
        source_row_hash="a" * 64,
        raw_payload={"Email": client.email_normalized, "Name": client.display_name},
        questionnaire_version="fixture-v1",
        submitted_at=datetime(2026, 1, 15, 10, 30, tzinfo=UTC),
    )
    assets = extract_questionnaire_assets(
        {
            "Feels Like Me images": "https://example.test/feels.jpg",
            "Not Me image": "https://example.test/not-me.jpg",
        },
        version="fixture-v1",
    )

    result = await LocalAssetWorkspace(tmp_path).register_submission(
        client=client,
        submission=submission,
        assets=assets,
    )

    submission_directory = tmp_path / "clients" / client.id / "submissions" / submission.id
    questionnaire = json.loads((submission_directory / "questionnaire.json").read_text())
    manifest = json.loads((submission_directory / "manifest.json").read_text())

    assert result.manifest_relative_path == (
        f"clients/{client.id}/submissions/{submission.id}/manifest.json"
    )
    assert questionnaire["raw_payload"]["Email"] == client.email_normalized
    assert manifest["downloaded"] is False
    assert [item["field_key"] for item in manifest["assets"]] == [
        "feels_like_me_images",
        "not_me_image",
    ]
    assert (submission_directory / "images" / "feels_like_me_images").is_dir()
    assert (submission_directory / "images" / "not_me_image").is_dir()


@pytest.mark.asyncio
async def test_import_registers_asset_workspace_for_new_submission(tmp_path: Path) -> None:
    clients = InMemoryClientRepository()
    submissions = InMemorySubmissionRepository()
    importer = QuestionnaireImportService(
        FixtureGoogleSheetsSource(
            [
                SheetRow(
                    row_number=2,
                    values={
                        "Email": "synthetic.client@example.test",
                        "Name": "Synthetic Client",
                        "Feels Like Me images": "https://example.test/feels.jpg",
                    },
                )
            ]
        ),
        clients,
        submissions,
        assets=LocalAssetWorkspace(tmp_path),
    )

    result = await importer.import_rows(
        ImportRequest(
            source=SheetReadRequest(
                spreadsheet_id="synthetic-spreadsheet",
                sheet_name="Form Responses 1",
            ),
            email_header="Email",
            display_name_header="Name",
            questionnaire_version="fixture-v1",
        )
    )

    client = next(iter(clients.items.values()))
    submission = next(iter(submissions.items.values()))
    manifest_path = (
        tmp_path / "clients" / client.id / "submissions" / submission.id / "manifest.json"
    )

    assert result.created_submissions == 1
    assert manifest_path.exists()
