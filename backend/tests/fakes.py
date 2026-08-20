from app.domain.contracts import ClientRecord, ClientSummary, QuestionnaireSubmission


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
