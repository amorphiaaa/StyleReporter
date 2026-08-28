from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

JsonObject = Mapping[str, Any]


@dataclass(frozen=True)
class ClientRecord:
    id: str
    email_normalized: str
    display_name: str | None = None


@dataclass(frozen=True)
class ClientSummary:
    client: ClientRecord
    submission_count: int


@dataclass(frozen=True)
class QuestionnaireSubmission:
    id: str
    client_id: str
    source_type: str
    source_spreadsheet_id: str
    source_sheet_name: str
    source_row_number: int
    source_row_hash: str
    raw_payload: JsonObject
    questionnaire_version: str | None = None
    submitted_at: datetime | None = None
    imported_at: datetime | None = None


@dataclass(frozen=True)
class QuestionnaireAsset:
    """An image reference extracted from a questionnaire submission."""

    field_key: str
    ordinal: int
    source_url: str
    drive_folder: str | None = None


@dataclass(frozen=True)
class AssetDownloadResult:
    """Provider result for one attempted image download."""

    status: str
    filename: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class AssetWorkspaceResult:
    """The filesystem workspace created for one client submission."""

    client_directory: str
    submission_directory: str
    manifest_relative_path: str
    asset_count: int
    downloaded_count: int = 0


@dataclass(frozen=True)
class AssetPublicationResult:
    """Result of publishing a local submission workspace to a provider."""

    client_folder_id: str
    subfolder_ids: Mapping[str, str]
    uploaded_count: int
    skipped_count: int


@dataclass(frozen=True)
class ManualStyleReport:
    """User-authored report content associated with one submission."""

    id: str
    client_id: str
    submission_id: str
    content: JsonObject
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class SheetReadRequest:
    spreadsheet_id: str
    sheet_name: str
    cell_range: str | None = None


@dataclass(frozen=True)
class SheetRow:
    row_number: int
    values: Mapping[str, str]


@dataclass(frozen=True)
class ImportRequest:
    source: SheetReadRequest
    email_header: str
    display_name_header: str | None = None
    timestamp_header: str | None = "Timestamp"
    source_type: str = "google_sheets"
    questionnaire_version: str | None = None
    refresh_existing: bool = False
    import_id: str | None = None


@dataclass(frozen=True)
class ImportRowError:
    row_number: int
    code: str
    message: str


@dataclass(frozen=True)
class ImportResult:
    import_id: str
    rows_seen: int
    created_clients: int
    updated_clients: int
    created_submissions: int
    rejected_rows: int
    skipped_duplicates: int
    errors: Sequence[ImportRowError]


class ClientRepository(Protocol):
    async def list_summaries(self, search: str | None = None) -> Sequence[ClientSummary]:
        ...

    async def get_by_id(self, client_id: str) -> ClientRecord | None:
        ...

    async def get_by_normalized_email(self, email: str) -> ClientRecord | None:
        ...

    async def save(self, client: ClientRecord) -> ClientRecord:
        ...


class SubmissionRepository(Protocol):
    async def get_by_id(self, submission_id: str) -> QuestionnaireSubmission | None:
        ...

    async def get_by_source_row(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        row_number: int,
    ) -> QuestionnaireSubmission | None:
        ...

    async def save(self, submission: QuestionnaireSubmission) -> QuestionnaireSubmission:
        ...

    async def list_by_client_id(self, client_id: str) -> Sequence[QuestionnaireSubmission]:
        ...


class ManualStyleReportRepository(Protocol):
    async def get_by_submission_id(self, submission_id: str) -> ManualStyleReport | None:
        ...

    async def save(self, report: ManualStyleReport) -> ManualStyleReport:
        ...


class GoogleSheetsSource(Protocol):
    async def read_rows(self, request: SheetReadRequest) -> Sequence[SheetRow]:
        ...


class QuestionnaireImporter(Protocol):
    async def import_rows(self, request: ImportRequest) -> ImportResult:
        ...


class AssetWorkspace(Protocol):
    async def register_submission(
        self,
        *,
        client: ClientRecord,
        submission: QuestionnaireSubmission,
        assets: Sequence[QuestionnaireAsset],
    ) -> AssetWorkspaceResult:
        ...

    async def get_verified_image_paths(
        self,
        *,
        client_id: str,
        submission_id: str,
    ) -> Sequence[str]:
        ...


class AssetPublisher(Protocol):
    async def publish_submission(
        self,
        *,
        client: ClientRecord,
        submission: QuestionnaireSubmission,
        workspace: AssetWorkspaceResult,
    ) -> AssetPublicationResult:
        ...


class AssetDownloader(Protocol):
    async def download(
        self,
        *,
        source_url: str,
        destination_stem: Path,
    ) -> AssetDownloadResult:
        ...
