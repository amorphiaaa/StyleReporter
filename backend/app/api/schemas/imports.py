from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.contracts import ImportRequest, SheetReadRequest, SheetRow


class ImportRowPayload(BaseModel):
    row_number: int = Field(ge=1)
    values: dict[str, str]

    def to_domain(self) -> SheetRow:
        return SheetRow(row_number=self.row_number, values=self.values)


class ManualImportRequest(BaseModel):
    spreadsheet_id: str = Field(min_length=1, max_length=255)
    sheet_name: str = Field(min_length=1, max_length=255)
    cell_range: str | None = None
    email_header: str = Field(min_length=1, max_length=255)
    display_name_header: str | None = Field(default=None, max_length=255)
    timestamp_header: str | None = Field(default="Timestamp", max_length=255)
    source_type: str = Field(default="google_sheets", min_length=1, max_length=50)
    questionnaire_version: str | None = Field(default=None, max_length=100)
    rows: list[ImportRowPayload] = Field(min_length=1)

    def to_domain(self, import_id: UUID) -> ImportRequest:
        return ImportRequest(
            source=SheetReadRequest(
                spreadsheet_id=self.spreadsheet_id,
                sheet_name=self.sheet_name,
                cell_range=self.cell_range,
            ),
            email_header=self.email_header,
            display_name_header=self.display_name_header,
            timestamp_header=self.timestamp_header,
            source_type=self.source_type,
            questionnaire_version=self.questionnaire_version,
            import_id=str(import_id),
        )

    def rows_to_domain(self) -> list[SheetRow]:
        return [row.to_domain() for row in self.rows]


class GoogleSheetsSyncRequest(BaseModel):
    spreadsheet_id: str | None = Field(default=None, min_length=1, max_length=255)
    sheet_name: str | None = Field(default=None, min_length=1, max_length=255)
    cell_range: str | None = Field(default=None, max_length=255)
    email_header: str = Field(default="Email", min_length=1, max_length=255)
    display_name_header: str | None = Field(default="Name", max_length=255)
    timestamp_header: str | None = Field(default="Timestamp", max_length=255)
    source_type: str = Field(default="google_sheets", min_length=1, max_length=50)
    questionnaire_version: str | None = Field(default=None, max_length=100)


class ImportErrorResponse(BaseModel):
    row_number: int
    code: str
    message: str


class ImportResponse(BaseModel):
    import_id: UUID
    rows_seen: int
    created_clients: int
    updated_clients: int
    created_submissions: int
    rejected_rows: int
    skipped_duplicates: int
    errors: list[ImportErrorResponse]


class ImportRunResponse(BaseModel):
    import_id: UUID
    source_type: str
    spreadsheet_id: str
    sheet_name: str
    status: str
    rows_seen: int
    created_clients: int
    updated_clients: int
    created_submissions: int
    rejected_rows: int
    skipped_duplicates: int
    row_errors: list[ImportErrorResponse]
    started_at: datetime
    completed_at: datetime | None
