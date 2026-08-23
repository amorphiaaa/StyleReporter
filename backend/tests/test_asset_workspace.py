import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.domain.contracts import (
    ClientRecord,
    ImportRequest,
    QuestionnaireAsset,
    QuestionnaireSubmission,
    SheetReadRequest,
    SheetRow,
)
from app.domain.questionnaire import extract_questionnaire_assets
from app.integrations.asset_downloader import HttpAssetDownloader
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


@pytest.mark.asyncio
async def test_workspace_downloads_assets_and_exposes_verified_paths(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "image/jpeg"},
            content=b"synthetic-image",
            request=request,
        )

    client = ClientRecord(
        id="client-download",
        email_normalized="download@example.test",
    )
    submission = QuestionnaireSubmission(
        id="submission-download",
        client_id=client.id,
        source_type="manual",
        source_spreadsheet_id="synthetic",
        source_sheet_name="Form Responses 1",
        source_row_number=2,
        source_row_hash="b" * 64,
        raw_payload={"Email": client.email_normalized},
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        workspace = LocalAssetWorkspace(
            tmp_path,
            downloader=HttpAssetDownloader(client=http_client),
        )
        result = await workspace.register_submission(
            client=client,
            submission=submission,
            assets=(
                QuestionnaireAsset(
                    field_key="feels_like_me_images",
                    ordinal=1,
                    source_url="https://example.test/looks-like-me",
                ),
            )
        )
        verified = await workspace.get_verified_image_paths(
            client_id=client.id,
            submission_id=submission.id,
        )

    assert result.downloaded_count == 1
    assert verified == [
        f"clients/{client.id}/submissions/{submission.id}/images/feels_like_me_images/01.jpg"
    ]
