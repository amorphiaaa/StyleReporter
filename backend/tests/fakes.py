from pathlib import Path

from app.domain.contracts import (
    CanvaAutofillJob,
    CanvaExportJob,
    CanvaFieldType,
    CanvaTemplateDefinition,
    ClientRecord,
    ClientSummary,
    QuestionnaireSubmission,
)


class InMemoryClientRepository:
    def __init__(self) -> None:
        self.items: dict[str, ClientRecord] = {}

    async def get_by_normalized_email(self, email: str) -> ClientRecord | None:
        return self.items.get(email)

    async def list_summaries(self, search: str | None = None) -> list[ClientSummary]:
        clients = list(self.items.values())
        if search:
            normalized_search = search.casefold()
            clients = [
                client
                for client in clients
                if normalized_search in client.email_normalized.casefold()
                or normalized_search in (client.display_name or "").casefold()
            ]
        return [
            ClientSummary(client=client, submission_count=0)
            for client in clients
        ]

    async def get_by_id(self, client_id: str) -> ClientRecord | None:
        return next((client for client in self.items.values() if client.id == client_id), None)

    async def save(self, client: ClientRecord) -> ClientRecord:
        self.items[client.email_normalized] = client
        return client


class InMemorySubmissionRepository:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str, int], QuestionnaireSubmission] = {}

    async def get_by_source_row(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        row_number: int,
    ) -> QuestionnaireSubmission | None:
        return self.items.get((spreadsheet_id, sheet_name, row_number))

    async def save(self, submission: QuestionnaireSubmission) -> QuestionnaireSubmission:
        key = (
            submission.source_spreadsheet_id,
            submission.source_sheet_name,
            submission.source_row_number,
        )
        self.items[key] = submission
        return submission

    async def list_by_client_id(self, client_id: str) -> list[QuestionnaireSubmission]:
        return [
            submission
            for submission in self.items.values()
            if submission.client_id == client_id
        ]


class InMemoryCanvaDesignProvider:
    """Deterministic Canva substitute for service and API tests."""

    def __init__(self) -> None:
        self.uploads: dict[str, Path] = {}
        self.autofill_jobs: dict[str, CanvaAutofillJob] = {}
        self.export_jobs: dict[str, CanvaExportJob] = {}
        self.autofill_requests: list[tuple[str, dict[str, str], dict[str, str]]] = []

    async def get_template_dataset(self, template_id: str) -> dict[str, CanvaFieldType]:
        return {"REPORT_TITLE": "text", "PROFILE_IMAGE": "image"}

    async def upload_asset(self, *, local_path: Path, name: str) -> str:
        asset_id = f"asset-{len(self.uploads) + 1}"
        self.uploads[asset_id] = local_path
        return asset_id

    async def create_autofill_job(
        self,
        *,
        template: CanvaTemplateDefinition,
        values: dict[str, str],
        asset_ids: dict[str, str],
    ) -> CanvaAutofillJob:
        job_id = f"autofill-{len(self.autofill_jobs) + 1}"
        design_id = f"design-{len(self.autofill_jobs) + 1}"
        job = CanvaAutofillJob(
            job_id=job_id,
            status="succeeded",
            design_id=design_id,
            design_url=f"https://canva.example/designs/{design_id}",
        )
        self.autofill_jobs[job_id] = job
        self.autofill_requests.append((template.key, dict(values), dict(asset_ids)))
        return job

    async def get_autofill_job(self, *, job_id: str) -> CanvaAutofillJob:
        return self.autofill_jobs[job_id]

    async def create_export_job(self, *, design_id: str, file_type: str = "pdf") -> CanvaExportJob:
        job_id = f"export-{len(self.export_jobs) + 1}"
        job = CanvaExportJob(
            job_id=job_id,
            status="succeeded",
            download_url=f"https://canva.example/exports/{design_id}.{file_type}",
        )
        self.export_jobs[job_id] = job
        return job

    async def get_export_job(self, *, job_id: str) -> CanvaExportJob:
        return self.export_jobs[job_id]
