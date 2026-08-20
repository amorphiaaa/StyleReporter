from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

JsonObject = Mapping[str, Any]


@dataclass(frozen=True)
class ClientRecord:
    id: str
    email_normalized: str
    display_name: str | None = None


@dataclass(frozen=True)
class QuestionnaireSubmission:
    id: str
    client_id: str
    source_type: str
    source_spreadsheet_id: str
    source_sheet_name: str
    source_row_number: int
    raw_payload: JsonObject
    submitted_at: datetime | None = None


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


@dataclass(frozen=True)
class ImportResult:
    import_id: str
    created_clients: int
    updated_clients: int
    created_submissions: int
    rejected_rows: int
    errors: Sequence[str]


@dataclass(frozen=True)
class AgentRunRequest:
    client_id: str
    submission_id: str
    context: JsonObject


@dataclass(frozen=True)
class AgentRunResult:
    status: str
    output: str | None = None


@dataclass(frozen=True)
class ConnectorStatus:
    configured: bool
    message: str


class ClientRepository(Protocol):
    async def get_by_normalized_email(self, email: str) -> ClientRecord | None:
        ...

    async def save(self, client: ClientRecord) -> ClientRecord:
        ...


class SubmissionRepository(Protocol):
    async def save(self, submission: QuestionnaireSubmission) -> QuestionnaireSubmission:
        ...


class GoogleSheetsSource(Protocol):
    async def read_rows(self, request: SheetReadRequest) -> Sequence[SheetRow]:
        ...


class QuestionnaireImporter(Protocol):
    async def import_rows(self, request: ImportRequest) -> ImportResult:
        ...


class AgentRuntime(Protocol):
    async def run(self, request: AgentRunRequest) -> AgentRunResult:
        ...


class CanvaConnector(Protocol):
    async def healthcheck(self) -> ConnectorStatus:
        ...


class CanvaSkill(Protocol):
    @property
    def name(self) -> str:
        ...

    @property
    def description(self) -> str:
        ...
