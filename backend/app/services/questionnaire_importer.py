from uuid import uuid4

from app.domain.contracts import (
    ClientRecord,
    ClientRepository,
    GoogleSheetsSource,
    ImportRequest,
    ImportResult,
    ImportRowError,
    QuestionnaireImporter,
    QuestionnaireSubmission,
    SubmissionRepository,
)
from app.domain.normalization import (
    hash_row,
    normalize_display_name,
    normalize_email,
    parse_submission_timestamp,
)


class QuestionnaireImportService(QuestionnaireImporter):
    """Import source rows through provider-agnostic repository contracts."""

    def __init__(
        self,
        source: GoogleSheetsSource,
        clients: ClientRepository,
        submissions: SubmissionRepository,
    ) -> None:
        self._source = source
        self._clients = clients
        self._submissions = submissions

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
            email = normalize_email(raw_payload.get(request.email_header))
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

            display_name = (
                normalize_display_name(raw_payload.get(request.display_name_header))
                if request.display_name_header
                else None
            )
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
            await self._submissions.save(
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
            created_submissions += 1

        return ImportResult(
            import_id=str(uuid4()),
            rows_seen=len(rows),
            created_clients=created_clients,
            updated_clients=updated_clients,
            created_submissions=created_submissions,
            rejected_rows=rejected_rows,
            skipped_duplicates=skipped_duplicates,
            errors=errors,
        )


class ScaffoldQuestionnaireImporter(QuestionnaireImporter):
    """Future orchestration boundary for source rows and repositories."""

    async def import_rows(self, request: ImportRequest) -> ImportResult:
        raise NotImplementedError(
            "Questionnaire import is intentionally not implemented in the scaffold."
        )
