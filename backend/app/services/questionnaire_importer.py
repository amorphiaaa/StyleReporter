from uuid import uuid4

from app.domain.contracts import (
    AssetWorkspace,
    ClientRecord,
    ClientRepository,
    GoogleSheetsSource,
    ImportRequest,
    ImportResult,
    ImportRowError,
    QuestionnaireImporter,
    QuestionnaireSubmission,
    SheetRow,
    SubmissionRepository,
)
from app.domain.normalization import (
    hash_row,
    normalize_display_name,
    normalize_email,
    parse_submission_timestamp,
)
from app.domain.questionnaire import (
    extract_questionnaire_assets,
    normalize_questionnaire_payload,
)


class QuestionnaireImportService(QuestionnaireImporter):
    """Import source rows through provider-agnostic repository contracts."""

    def __init__(
        self,
        source: GoogleSheetsSource,
        clients: ClientRepository,
        submissions: SubmissionRepository,
        assets: AssetWorkspace | None = None,
    ) -> None:
        self._source = source
        self._clients = clients
        self._submissions = submissions
        self._assets = assets

    async def import_rows(self, request: ImportRequest) -> ImportResult:
        rows = await self._source.read_rows(request.source)
        errors: list[ImportRowError] = []
        seen_source_rows: set[int] = set()
        created_clients = 0
        updated_clients = 0
        created_submissions = 0
        rejected_rows = 0
        skipped_duplicates = 0

        for row in rows:
            if row.row_number in seen_source_rows:
                skipped_duplicates += 1
                continue
            seen_source_rows.add(row.row_number)

            existing_submission = await self._submissions.get_by_source_row(
                request.source.spreadsheet_id,
                request.source.sheet_name,
                row.row_number,
            )
            if existing_submission is not None:
                skipped_duplicates += 1
                if request.refresh_existing:
                    updated_clients += await self._refresh_existing_submission(
                        existing_submission,
                        row,
                        request,
                    )
                continue

            if row.row_number < 1:
                rejected_rows += 1
                errors.append(
                    ImportRowError(
                        row_number=row.row_number,
                        code="invalid_row_number",
                        message="Source row number must be a positive integer.",
                    )
                )
                continue

            raw_payload = dict(row.values)
            questionnaire = normalize_questionnaire_payload(
                raw_payload,
                version=request.questionnaire_version,
                email_header=request.email_header,
                display_name_header=request.display_name_header,
            )
            email = normalize_email(questionnaire.email)
            if email is None:
                rejected_rows += 1
                errors.append(
                    ImportRowError(
                        row_number=row.row_number,
                        code="invalid_email",
                        message=f"Column {request.email_header!r} is empty or invalid.",
                    )
                )
                continue

            display_name = normalize_display_name(questionnaire.display_name)
            existing_client = await self._clients.get_by_normalized_email(email)
            if existing_client is None:
                client = await self._clients.save(
                    ClientRecord(
                        id=str(uuid4()),
                        email_normalized=email,
                        display_name=display_name,
                    )
                )
                created_clients += 1
            else:
                client = existing_client
                if display_name and display_name != existing_client.display_name:
                    client = await self._clients.save(
                        ClientRecord(
                            id=existing_client.id,
                            email_normalized=existing_client.email_normalized,
                            display_name=display_name,
                        )
                    )
                    updated_clients += 1

            timestamp = (
                parse_submission_timestamp(raw_payload.get(request.timestamp_header))
                if request.timestamp_header
                else None
            )
            saved_submission = await self._submissions.save(
                QuestionnaireSubmission(
                    id=str(uuid4()),
                    client_id=client.id,
                    source_type=request.source_type,
                    source_spreadsheet_id=request.source.spreadsheet_id,
                    source_sheet_name=request.source.sheet_name,
                    source_row_number=row.row_number,
                    raw_payload=raw_payload,
                    source_row_hash=hash_row(raw_payload),
                    questionnaire_version=request.questionnaire_version,
                    submitted_at=timestamp,
                )
            )
            if self._assets is not None:
                await self._assets.register_submission(
                    client=client,
                    submission=saved_submission,
                    assets=extract_questionnaire_assets(
                        raw_payload,
                        version=request.questionnaire_version,
                    ),
                )
            created_submissions += 1

        return ImportResult(
            import_id=request.import_id or str(uuid4()),
            rows_seen=len(rows),
            created_clients=created_clients,
            updated_clients=updated_clients,
            created_submissions=created_submissions,
            rejected_rows=rejected_rows,
            skipped_duplicates=skipped_duplicates,
            errors=errors,
        )

    async def _refresh_existing_submission(
        self,
        existing_submission: QuestionnaireSubmission,
        row: SheetRow,
        request: ImportRequest,
    ) -> int:
        questionnaire = normalize_questionnaire_payload(
            row.values,
            version=request.questionnaire_version,
            email_header=request.email_header,
            display_name_header=request.display_name_header,
        )
        email = normalize_email(questionnaire.email)
        if email is None:
            return 0

        client = await self._clients.get_by_id(existing_submission.client_id)
        updated_clients = 0
        if client is not None:
            display_name = normalize_display_name(questionnaire.display_name)
            if display_name and not client.display_name:
                client = await self._clients.save(
                    ClientRecord(
                        id=client.id,
                        email_normalized=client.email_normalized,
                        display_name=display_name,
                    )
                )
                updated_clients = 1

        timestamp = (
            parse_submission_timestamp(row.values.get(request.timestamp_header))
            if request.timestamp_header
            else None
        )
        saved_submission = await self._submissions.save(
            QuestionnaireSubmission(
                id=existing_submission.id,
                client_id=existing_submission.client_id,
                source_type=request.source_type,
                source_spreadsheet_id=request.source.spreadsheet_id,
                source_sheet_name=request.source.sheet_name,
                source_row_number=row.row_number,
                raw_payload=dict(row.values),
                source_row_hash=hash_row(dict(row.values)),
                questionnaire_version=request.questionnaire_version,
                submitted_at=timestamp,
                imported_at=existing_submission.imported_at,
            )
        )
        if self._assets is not None:
            await self._assets.register_submission(
                client=client or ClientRecord(
                    id=existing_submission.client_id,
                    email_normalized=email,
                ),
                submission=saved_submission,
                assets=extract_questionnaire_assets(
                    row.values,
                    version=request.questionnaire_version,
                ),
            )
        return updated_clients


class ScaffoldQuestionnaireImporter(QuestionnaireImporter):
    """Future orchestration boundary for source rows and repositories."""

    async def import_rows(self, request: ImportRequest) -> ImportResult:
        raise NotImplementedError(
            "Questionnaire import is intentionally not implemented in the scaffold."
        )
