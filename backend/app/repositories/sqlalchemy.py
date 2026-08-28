from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Client
from app.db.models import ManualStyleReport as ManualStyleReportModel
from app.db.models import QuestionnaireSubmission as QuestionnaireSubmissionModel
from app.domain.contracts import (
    ClientRecord,
    ClientRepository,
    ClientSummary,
    ManualStyleReportRepository,
    QuestionnaireSubmission,
    SubmissionRepository,
)
from app.domain.contracts import (
    ManualStyleReport as ManualStyleReportRecord,
)


class SqlAlchemyClientRepository(ClientRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_summaries(self, search: str | None = None) -> list[ClientSummary]:
        statement = (
            select(Client, func.count(QuestionnaireSubmissionModel.id))
            .outerjoin(
                QuestionnaireSubmissionModel,
                QuestionnaireSubmissionModel.client_id == Client.id,
            )
            .group_by(Client.id)
            .order_by(Client.created_at.desc())
        )
        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(
                    Client.email_normalized.ilike(pattern),
                    Client.display_name.ilike(pattern),
                )
            )

        result = await self._session.execute(statement)
        return [
            ClientSummary(client=_to_client_record(model), submission_count=count)
            for model, count in result.all()
        ]

    async def get_by_id(self, client_id: str) -> ClientRecord | None:
        model = await self._session.get(Client, UUID(client_id))
        return _to_client_record(model) if model else None

    async def get_by_normalized_email(self, email: str) -> ClientRecord | None:
        result = await self._session.execute(
            select(Client).where(Client.email_normalized == email)
        )
        model = result.scalar_one_or_none()
        return _to_client_record(model) if model else None

    async def save(self, client: ClientRecord) -> ClientRecord:
        model = await self._session.get(Client, UUID(client.id))
        if model is None:
            model = Client(
                id=UUID(client.id),
                email_normalized=client.email_normalized,
                display_name=client.display_name,
            )
            self._session.add(model)
        else:
            model.email_normalized = client.email_normalized
            model.display_name = client.display_name

        await self._session.flush()
        return _to_client_record(model)


class SqlAlchemySubmissionRepository(SubmissionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, submission_id: str) -> QuestionnaireSubmission | None:
        model = await self._session.get(QuestionnaireSubmissionModel, UUID(submission_id))
        return _to_submission_record(model) if model else None

    async def get_by_source_row(
        self,
        spreadsheet_id: str,
        sheet_name: str,
        row_number: int,
    ) -> QuestionnaireSubmission | None:
        result = await self._session.execute(
            select(QuestionnaireSubmissionModel).where(
                QuestionnaireSubmissionModel.source_spreadsheet_id == spreadsheet_id,
                QuestionnaireSubmissionModel.source_sheet_name == sheet_name,
                QuestionnaireSubmissionModel.source_row_number == row_number,
            )
        )
        model = result.scalar_one_or_none()
        return _to_submission_record(model) if model else None

    async def save(self, submission: QuestionnaireSubmission) -> QuestionnaireSubmission:
        model = await self._session.get(
            QuestionnaireSubmissionModel,
            UUID(submission.id),
        )
        if model is None:
            model = QuestionnaireSubmissionModel(
                id=UUID(submission.id),
                client_id=UUID(submission.client_id),
                source_type=submission.source_type,
                source_spreadsheet_id=submission.source_spreadsheet_id,
                source_sheet_name=submission.source_sheet_name,
                source_row_number=submission.source_row_number,
                source_row_hash=submission.source_row_hash,
                raw_payload=dict(submission.raw_payload),
                questionnaire_version=submission.questionnaire_version,
                submitted_at=submission.submitted_at,
            )
            self._session.add(model)
        else:
            model.client_id = UUID(submission.client_id)
            model.source_type = submission.source_type
            model.source_spreadsheet_id = submission.source_spreadsheet_id
            model.source_sheet_name = submission.source_sheet_name
            model.source_row_number = submission.source_row_number
            model.source_row_hash = submission.source_row_hash
            model.raw_payload = dict(submission.raw_payload)
            model.questionnaire_version = submission.questionnaire_version
            model.submitted_at = submission.submitted_at

        await self._session.flush()
        return _to_submission_record(model)

    async def list_by_client_id(self, client_id: str) -> list[QuestionnaireSubmission]:
        result = await self._session.execute(
            select(QuestionnaireSubmissionModel)
            .where(QuestionnaireSubmissionModel.client_id == UUID(client_id))
            .order_by(QuestionnaireSubmissionModel.source_row_number.asc())
        )
        return [_to_submission_record(model) for model in result.scalars().all()]


class SqlAlchemyManualStyleReportRepository(ManualStyleReportRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_submission_id(
        self, submission_id: str
    ) -> ManualStyleReportRecord | None:
        result = await self._session.execute(
            select(ManualStyleReportModel).where(
                ManualStyleReportModel.submission_id == UUID(submission_id)
            )
        )
        model = result.scalar_one_or_none()
        return _to_manual_style_report(model) if model else None

    async def save(self, report: ManualStyleReportRecord) -> ManualStyleReportRecord:
        model = await self._session.get(ManualStyleReportModel, UUID(report.id))
        if model is None:
            model = ManualStyleReportModel(
                id=UUID(report.id),
                client_id=UUID(report.client_id),
                submission_id=UUID(report.submission_id),
                content=dict(report.content),
            )
            self._session.add(model)
        else:
            model.client_id = UUID(report.client_id)
            model.submission_id = UUID(report.submission_id)
            model.content = dict(report.content)

        await self._session.flush()
        return _to_manual_style_report(model)


def _to_client_record(model: Client) -> ClientRecord:
    return ClientRecord(
        id=str(model.id),
        email_normalized=model.email_normalized,
        display_name=model.display_name,
    )


def _to_submission_record(model: QuestionnaireSubmissionModel) -> QuestionnaireSubmission:
    return QuestionnaireSubmission(
        id=str(model.id),
        client_id=str(model.client_id),
        source_type=model.source_type,
        source_spreadsheet_id=model.source_spreadsheet_id,
        source_sheet_name=model.source_sheet_name,
        source_row_number=model.source_row_number,
        source_row_hash=model.source_row_hash,
        raw_payload=model.raw_payload,
        questionnaire_version=model.questionnaire_version,
        submitted_at=model.submitted_at,
        imported_at=model.imported_at,
    )


def _to_manual_style_report(model: ManualStyleReportModel) -> ManualStyleReportRecord:
    return ManualStyleReportRecord(
        id=str(model.id),
        client_id=str(model.client_id),
        submission_id=str(model.submission_id),
        content=model.content,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
