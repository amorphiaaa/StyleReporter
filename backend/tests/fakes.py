from app.domain.contracts import ClientRecord, QuestionnaireSubmission


class InMemoryClientRepository:
    def __init__(self) -> None:
        self.items: dict[str, ClientRecord] = {}

    async def get_by_normalized_email(self, email: str) -> ClientRecord | None:
        return self.items.get(email)

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
