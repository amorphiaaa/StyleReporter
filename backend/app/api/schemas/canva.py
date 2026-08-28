from typing import Literal

from pydantic import BaseModel, ConfigDict


class CanvaReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    export_pdf: bool = True


class CanvaReportResponse(BaseModel):
    status: Literal["success", "failed"]
    autofill_job_id: str
    design_id: str | None = None
    design_url: str | None = None
    export_job_id: str | None = None
    pdf_url: str | None = None
    text_fields_filled: int
    image_fields_filled: int
