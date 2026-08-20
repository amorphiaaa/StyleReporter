from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ClientListItem(BaseModel):
    id: UUID
    email_normalized: str
    display_name: str | None
    submission_count: int


class ClientSubmissionResponse(BaseModel):
    id: UUID
    source_type: str
    spreadsheet_id: str
    sheet_name: str
    source_row_number: int
    source_row_hash: str
    questionnaire_version: str | None
    submitted_at: datetime | None
    imported_at: datetime | None
    raw_payload: dict[str, Any]


class ClientDetailResponse(BaseModel):
    id: UUID
    email_normalized: str
    display_name: str | None
    submissions: list[ClientSubmissionResponse]


class UpdateClientRequest(BaseModel):
    display_name: str | None = Field(..., max_length=255)

    @field_validator("display_name", mode="before")
    @classmethod
    def trim_display_name(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value


class ClientUpdateResponse(BaseModel):
    id: UUID
    email_normalized: str
    display_name: str | None
