import json
import re
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.domain.contracts import ClientRecord, QuestionnaireSubmission
from app.domain.questionnaire import extract_questionnaire_assets
from app.integrations.asset_downloader import HttpAssetDownloader
from app.integrations.google_drive_storage import (
    DRIVE_FOLDER_NAMES,
    GoogleDriveWorkspacePublisher,
)
from app.services.asset_workspace import LocalAssetWorkspace


class FakeTokenProvider:
    async def get_access_token(self) -> str:
        return "synthetic-token"


def _drive_handler(state: dict[str, dict[str, str]], created_names: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            query = request.url.params.get("q", "")
            match = re.search(r"value='([^']+)'", query)
            key = match.group(1) if match else ""
            entry = state.get(key)
            return httpx.Response(
                200,
                json={"files": [entry] if entry else []},
                request=request,
            )

        if request.method == "POST" and "upload" not in request.url.path:
            metadata = json.loads(request.content)
            key = metadata["appProperties"]["stylereporter_key"]
            entry = {
                "id": f"drive-{len(state) + 1}",
                "name": metadata["name"],
                "mimeType": metadata["mimeType"],
                "appProperties": metadata["appProperties"],
            }
            state[key] = entry
            created_names.append(metadata["name"])
            return httpx.Response(200, json=entry, request=request)

        if request.method == "POST" and "upload" in request.url.path:
            key_match = re.search(rb'"stylereporter_key"\s*:\s*"([^"]+)"', request.content)
            checksum_match = re.search(
                rb'"stylereporter_sha256"\s*:\s*"([^"]+)"', request.content
            )
            assert key_match is not None
            key = key_match.group(1).decode()
            app_properties = {
                "stylereporter_key": key,
                "stylereporter_sha256": checksum_match.group(1).decode()
                if checksum_match
                else "",
            }
            entry = {
                "id": f"drive-{len(state) + 1}",
                "name": key,
                "appProperties": app_properties,
            }
            state[key] = entry
            created_names.append(key)
            return httpx.Response(200, json=entry, request=request)

        raise AssertionError(f"Unexpected Drive request: {request.method} {request.url}")

    return handler


@pytest.mark.asyncio
async def test_google_drive_publisher_creates_expected_workspace_idempotently(
    tmp_path: Path,
) -> None:
    image_handler = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "image/jpeg"},
            content=b"synthetic-image",
            request=request,
        )
    )
    client = ClientRecord(
        id="client-drive-123",
        email_normalized="drive@example.test",
        display_name="Drive Client",
    )
    submission = QuestionnaireSubmission(
        id="submission-drive-456",
        client_id=client.id,
        source_type="google_sheets",
        source_spreadsheet_id="synthetic-spreadsheet",
        source_sheet_name="Form Responses 1",
        source_row_number=2,
        source_row_hash="a" * 64,
        raw_payload={"Email": client.email_normalized},
        questionnaire_version="fixture-v1",
        submitted_at=datetime(2026, 1, 15, 10, 30, tzinfo=UTC),
    )
    assets = extract_questionnaire_assets(
        {
            "Feels Like Me images": "https://example.test/feels.jpg",
        },
        version="fixture-v1",
    )

    async with httpx.AsyncClient(transport=image_handler) as image_client:
        workspace = LocalAssetWorkspace(
            tmp_path,
            downloader=HttpAssetDownloader(client=image_client),
        )
        workspace_result = await workspace.register_submission(
            client=client,
            submission=submission,
            assets=assets,
        )

    state: dict[str, dict[str, str]] = {}
    created_names: list[str] = []
    drive_transport = httpx.MockTransport(_drive_handler(state, created_names))
    async with httpx.AsyncClient(transport=drive_transport) as drive_client:
        publisher = GoogleDriveWorkspacePublisher(
            root_folder_id="root-folder",
            local_root=tmp_path,
            access_token_provider=FakeTokenProvider(),
            client=drive_client,
        )
        first = await publisher.publish_submission(
            client=client,
            submission=submission,
            workspace=workspace_result,
        )
        second = await publisher.publish_submission(
            client=client,
            submission=submission,
            workspace=workspace_result,
        )

    assert set(first.subfolder_ids) == set(DRIVE_FOLDER_NAMES)
    assert first.uploaded_count == 2
    assert first.skipped_count == 0
    assert second.uploaded_count == 0
    assert second.skipped_count == 2
    assert set(DRIVE_FOLDER_NAMES.values()).issubset(created_names)
    assert len(state) == 8  # client folder, five subfolders, questionnaire, image
