from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class GenerateStyleReportRequest(BaseModel):
    submission_id: UUID
    runtime: Literal["stub", "agents_sdk_dry_run"] = "stub"


class StyleReportResponse(BaseModel):
    id: UUID
    client_id: UUID
    submission_id: UUID
    status: str
    runtime_type: str
    report_version: str
    report: dict[str, Any] | None
    error_message: str | None
    created_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
