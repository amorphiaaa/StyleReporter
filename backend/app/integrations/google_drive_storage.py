"""Google Drive workspace publisher for client folders and questionnaire assets."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from app.domain.contracts import (
    AssetPublicationResult,
    AssetPublisher,
    AssetWorkspaceResult,
    ClientRecord,
    QuestionnaireSubmission,
)
from app.integrations.google_oauth import (
    GOOGLE_DRIVE_OAUTH_SCOPE,
    OAuthAccessTokenProvider,
)
from app.integrations.google_sheets import (
    GoogleSheetsConfigurationError,
    ServiceAccountAccessTokenProvider,
)

GOOGLE_DRIVE_READWRITE_SCOPE = "https://www.googleapis.com/auth/drive"
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
GOOGLE_DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
GOOGLE_DRIVE_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
DRIVE_APP_PROPERTY = "stylereporter_key"
DRIVE_CHECKSUM_PROPERTY = "stylereporter_sha256"

DRIVE_FOLDER_NAMES = {
    "questionnaire": "Questionnaire",
    "good_outfits": "Good Outfits",
    "bad_outfits": "Bad Outfits",
    "inspiration": "Inspiration",
    "final_report": "Final Report",
}

FIELD_TO_DRIVE_FOLDER = {
    "feels_like_me_images": "good_outfits",
    "not_me_image": "bad_outfits",
    "inspiration_images": "inspiration",
    "body_proportion_photo": "questionnaire",
}


class GoogleDriveStorageConfigurationError(ValueError):
    """Raised when Drive publishing is enabled without sufficient settings."""


class GoogleDriveStorageError(RuntimeError):
    """Raised when a Drive folder or file operation fails."""


class GoogleDriveWorkspacePublisher(AssetPublisher):
    """Create a stable client workspace and publish local evidence to Drive.

    Folder and file identities are stored in Drive ``appProperties`` rather
    than inferred from display names. This makes retries and client renames
    idempotent while keeping the folder names readable for the team.
    """

    def __init__(
        self,
        *,
        root_folder_id: str,
        local_root: Path,
        access_token_provider: Any,
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not root_folder_id.strip():
            raise GoogleDriveStorageConfigurationError(
                "Google Drive storage requires GOOGLE_DRIVE_ROOT_FOLDER_ID."
            )
        self.root_folder_id = root_folder_id.strip()
        self.local_root = local_root.resolve()
        self.access_token_provider = access_token_provider
        self.timeout_seconds = timeout_seconds
        self.client = client

    @classmethod
    def from_service_account_json(
        cls,
        service_account_json: str,
        *,
        root_folder_id: str,
        local_root: Path,
        timeout_seconds: float = 30.0,
    ) -> GoogleDriveWorkspacePublisher:
        try:
            provider = ServiceAccountAccessTokenProvider(
                service_account_json,
                scopes=(GOOGLE_DRIVE_READWRITE_SCOPE,),
            )
        except GoogleSheetsConfigurationError as exc:
            raise GoogleDriveStorageConfigurationError(str(exc)) from exc
        return cls(
            root_folder_id=root_folder_id,
            local_root=local_root,
            access_token_provider=provider,
            timeout_seconds=timeout_seconds,
        )

    @classmethod
    def from_oauth(
        cls,
        client_json: str,
        refresh_token: str,
        *,
        root_folder_id: str,
        local_root: Path,
        timeout_seconds: float = 30.0,
    ) -> GoogleDriveWorkspacePublisher:
        return cls(
            root_folder_id=root_folder_id,
            local_root=local_root,
            access_token_provider=OAuthAccessTokenProvider(
                client_json,
                refresh_token,
                scopes=(GOOGLE_DRIVE_OAUTH_SCOPE,),
            ),
            timeout_seconds=timeout_seconds,
        )

    async def publish_submission(
        self,
        *,
        client: ClientRecord,
        submission: QuestionnaireSubmission,
        workspace: AssetWorkspaceResult,
    ) -> AssetPublicationResult:
        if self.client is not None:
            return await self._publish_with_client(self.client, client, submission, workspace)

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client_http:
            return await self._publish_with_client(client_http, client, submission, workspace)

    async def _publish_with_client(
        self,
        client_http: httpx.AsyncClient,
        client: ClientRecord,
        submission: QuestionnaireSubmission,
        workspace: AssetWorkspaceResult,
    ) -> AssetPublicationResult:
        try:
            token = await self.access_token_provider.get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            client_folder_id = await self._ensure_folder(
                client_http,
                headers=headers,
                parent_id=self.root_folder_id,
                name=_client_folder_name(client),
                key=f"client:{client.id}",
            )

            subfolder_ids: dict[str, str] = {}
            for folder_key, folder_name in DRIVE_FOLDER_NAMES.items():
                subfolder_ids[folder_key] = await self._ensure_folder(
                    client_http,
                    headers=headers,
                    parent_id=client_folder_id,
                    name=folder_name,
                    key=f"folder:{client.id}:{folder_key}",
                )

            uploaded_count = 0
            skipped_count = 0
            questionnaire_path = self._resolve_local_path(
                Path(workspace.submission_directory) / "questionnaire.json"
            )
            questionnaire_bytes = questionnaire_path.read_bytes()
            if await self._upsert_file(
                client_http,
                headers=headers,
                parent_id=subfolder_ids["questionnaire"],
                name=f"questionnaire-{submission.id}.json",
                key=f"questionnaire:{submission.id}",
                content_type="application/json",
                content=questionnaire_bytes,
                checksum=_sha256(questionnaire_bytes),
            ):
                uploaded_count += 1
            else:
                skipped_count += 1

            manifest_path = self._resolve_local_path(Path(workspace.manifest_relative_path))
            manifest = _read_manifest(manifest_path)
            for asset in manifest.get("assets", []):
                if not isinstance(asset, dict) or asset.get("status") != "downloaded":
                    continue
                local_relative_path = asset.get("local_relative_path")
                if not isinstance(local_relative_path, str):
                    continue
                image_path = self._resolve_local_path(Path(local_relative_path))
                image_bytes = image_path.read_bytes()
                folder_key = _asset_folder_key(asset)
                if folder_key not in subfolder_ids:
                    folder_key = "questionnaire"
                field_key = _safe_name(str(asset.get("field_key", "asset")))
                ordinal = int(asset.get("ordinal", 1))
                suffix = image_path.suffix.lower() or ".bin"
                image_name = f"{field_key}-{ordinal:02d}{suffix}"
                if await self._upsert_file(
                    client_http,
                    headers=headers,
                    parent_id=subfolder_ids[folder_key],
                    name=image_name,
                    key=f"asset:{submission.id}:{field_key}:{ordinal}",
                    content_type=str(asset.get("content_type") or "application/octet-stream"),
                    content=image_bytes,
                    checksum=str(asset.get("sha256") or _sha256(image_bytes)),
                ):
                    uploaded_count += 1
                else:
                    skipped_count += 1

            return AssetPublicationResult(
                client_folder_id=client_folder_id,
                subfolder_ids=subfolder_ids,
                uploaded_count=uploaded_count,
                skipped_count=skipped_count,
            )
        except (OSError, ValueError, TypeError) as exc:
            raise GoogleDriveStorageError(
                "Google Drive publishing could not read the local client workspace."
            ) from exc
        except httpx.HTTPError as exc:
            raise GoogleDriveStorageError(
                f"Google Drive request failed: {type(exc).__name__}."
            ) from exc

    async def _ensure_folder(
        self,
        client_http: httpx.AsyncClient,
        *,
        headers: dict[str, str],
        parent_id: str,
        name: str,
        key: str,
    ) -> str:
        existing = await self._find_file(
            client_http,
            headers=headers,
            parent_id=parent_id,
            key=key,
            mime_type=GOOGLE_DRIVE_FOLDER_MIME_TYPE,
        )
        if existing is not None:
            return _required_id(existing)

        response = await client_http.post(
            GOOGLE_DRIVE_FILES_URL,
            headers={**headers, "Content-Type": "application/json"},
            params={"fields": "id,name"},
            json={
                "name": name,
                "mimeType": GOOGLE_DRIVE_FOLDER_MIME_TYPE,
                "parents": [parent_id],
                "appProperties": {DRIVE_APP_PROPERTY: key},
            },
            timeout=self.timeout_seconds,
        )
        return _required_id(_response_json(response))

    async def _upsert_file(
        self,
        client_http: httpx.AsyncClient,
        *,
        headers: dict[str, str],
        parent_id: str,
        name: str,
        key: str,
        content_type: str,
        content: bytes,
        checksum: str,
    ) -> bool:
        existing = await self._find_file(
            client_http,
            headers=headers,
            parent_id=parent_id,
            key=key,
        )
        if existing is not None:
            app_properties = existing.get("appProperties") or {}
            if app_properties.get(DRIVE_CHECKSUM_PROPERTY) == checksum:
                return False
            file_id = _required_id(existing)
            response = await client_http.patch(
                f"{GOOGLE_DRIVE_UPLOAD_URL}/{file_id}",
                headers={**headers, "Content-Type": content_type},
                params={"uploadType": "media", "fields": "id,name"},
                content=content,
                timeout=self.timeout_seconds,
            )
            _response_json(response)
            metadata_response = await client_http.patch(
                f"{GOOGLE_DRIVE_FILES_URL}/{file_id}",
                headers={**headers, "Content-Type": "application/json"},
                params={"fields": "id,name"},
                json={
                    "name": name,
                    "appProperties": {
                        DRIVE_APP_PROPERTY: key,
                        DRIVE_CHECKSUM_PROPERTY: checksum,
                    },
                },
                timeout=self.timeout_seconds,
            )
            _response_json(metadata_response)
            return True

        boundary = f"stylereporter-{uuid4().hex}"
        metadata = {
            "name": name,
            "parents": [parent_id],
            "appProperties": {
                DRIVE_APP_PROPERTY: key,
                DRIVE_CHECKSUM_PROPERTY: checksum,
            },
        }
        body = _multipart_body(boundary, metadata, content_type, content)
        response = await client_http.post(
            GOOGLE_DRIVE_UPLOAD_URL,
            headers={
                **headers,
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
            params={"uploadType": "multipart", "fields": "id,name"},
            content=body,
            timeout=self.timeout_seconds,
        )
        _response_json(response)
        return True

    async def _find_file(
        self,
        client_http: httpx.AsyncClient,
        *,
        headers: dict[str, str],
        parent_id: str,
        key: str,
        mime_type: str | None = None,
    ) -> dict[str, Any] | None:
        conditions = [
            f"'{_escape_query_value(parent_id)}' in parents",
            "trashed = false",
            "appProperties has { key='stylereporter_key' "
            f"and value='{_escape_query_value(key)}' }}",
        ]
        if mime_type is not None:
            conditions.append(f"mimeType = '{_escape_query_value(mime_type)}'")
        response = await client_http.get(
            GOOGLE_DRIVE_FILES_URL,
            headers=headers,
            params={
                "q": " and ".join(conditions),
                "spaces": "drive",
                "pageSize": "10",
                "fields": "files(id,name,mimeType,appProperties)",
            },
            timeout=self.timeout_seconds,
        )
        payload = _response_json(response)
        files = payload.get("files", [])
        return files[0] if files else None

    def _resolve_local_path(self, relative_path: Path) -> Path:
        candidate = (self.local_root / relative_path).resolve()
        try:
            candidate.relative_to(self.local_root)
        except ValueError as exc:
            raise GoogleDriveStorageError(
                "Client workspace path escaped its configured root."
            ) from exc
        if not candidate.is_file():
            raise GoogleDriveStorageError(f"Client workspace file is missing: {relative_path}")
        return candidate


def _asset_folder_key(asset: dict[str, Any]) -> str:
    value = asset.get("drive_folder")
    if isinstance(value, str) and value in DRIVE_FOLDER_NAMES:
        return value
    field_key = asset.get("field_key")
    return FIELD_TO_DRIVE_FOLDER.get(str(field_key), "questionnaire")


def _client_folder_name(client: ClientRecord) -> str:
    display_name = (client.display_name or "Unnamed client").strip()
    display_name = re.sub(r"[\\/:*?\"<>|]+", "-", display_name).strip()
    return f"{display_name or 'Unnamed client'} [{client.id}]"


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")[:80] or "asset"


def _escape_query_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _multipart_body(
    boundary: str,
    metadata: dict[str, Any],
    content_type: str,
    content: bytes,
) -> bytes:
    metadata_bytes = json.dumps(metadata, ensure_ascii=False).encode("utf-8")
    return (
        f"--{boundary}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
    ).encode() + metadata_bytes + (
        f"\r\n--{boundary}\r\n"
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()


def _read_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("assets", []), list):
        raise ValueError("Asset manifest is invalid.")
    return payload


def _required_id(payload: dict[str, Any]) -> str:
    value = payload.get("id")
    if not isinstance(value, str) or not value:
        _raise_drive_response("Google Drive API response did not contain a file ID.")
    return value


def _response_json(response: httpx.Response) -> dict[str, Any]:
    if response.is_error:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        detail = payload.get("error", {}).get("message") if isinstance(payload, dict) else None
        _raise_drive_response(detail or "Google Drive API request failed.")
    try:
        payload = response.json()
    except ValueError as exc:
        raise GoogleDriveStorageError("Google Drive API returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise GoogleDriveStorageError("Google Drive API returned an invalid response.")
    return payload


def _raise_drive_response(detail: str) -> None:
    raise GoogleDriveStorageError(f"Google Drive API request failed: {detail}")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
