from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Protocol

JsonObject = Mapping[str, Any]
CanvaFieldType = Literal["text", "image"]


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
class CanvaTemplateField:
    """One technical field with human-readable placement guidance."""

    key: str
    field_type: CanvaFieldType
    page_number: int
    description: str
    required: bool = False
    max_characters: int | None = None


@dataclass(frozen=True)
class CanvaTemplatePage:
    """A page-level description supplied by the template author."""

    page_number: int
    description: str


@dataclass(frozen=True)
class CanvaTemplateDefinition:
    """Versioned, provider-neutral description of a Canva template."""

    key: str
    version: str
    brand_template_id: str | None
    pages: Sequence[CanvaTemplatePage]
    fields: Sequence[CanvaTemplateField]


@dataclass(frozen=True)
class CanvaPlacementAssignment:
    """One agent decision connecting report content to a template field."""

    field_key: str
    source_path: str
    rationale: str = ""


@dataclass(frozen=True)
class CanvaPlacementPlan:
    """Agent-produced plan for placing report content into a template."""

    assignments: Sequence[CanvaPlacementAssignment]
    unplaced_source_paths: Sequence[str] = ()


@dataclass(frozen=True)
class CanvaAutofillPayload:
    """Flattened report values ready for a Canva provider adapter."""

    template_key: str
    values: Mapping[str, str]
    asset_paths: Mapping[str, Path]


@dataclass(frozen=True)
class CanvaAutofillJob:
    """Status returned while Canva creates a design from a template."""

    job_id: str
    status: str
    design_id: str | None = None
    design_url: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class CanvaExportJob:
    """Status returned while Canva exports a completed design."""

    job_id: str
    status: str
    download_url: str | None = None
    error: str | None = None


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


class CanvaDesignProvider(Protocol):
    """Canva boundary; implementations may use Connect APIs or a test fake."""

    async def get_template_dataset(self, template_id: str) -> Mapping[str, CanvaFieldType]:
        ...

    async def upload_asset(self, *, local_path: Path, name: str) -> str:
        ...

    async def create_autofill_job(
        self,
        *,
        template: CanvaTemplateDefinition,
        values: Mapping[str, str],
        asset_ids: Mapping[str, str],
    ) -> CanvaAutofillJob:
        ...

    async def get_autofill_job(self, *, job_id: str) -> CanvaAutofillJob:
        ...

    async def create_export_job(self, *, design_id: str, file_type: str = "pdf") -> CanvaExportJob:
        ...

    async def get_export_job(self, *, job_id: str) -> CanvaExportJob:
        ...
