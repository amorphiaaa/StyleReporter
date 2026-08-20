from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.api.schemas.clients import (
    ClientDetailResponse,
    ClientListItem,
    ClientSubmissionResponse,
)
from app.repositories.sqlalchemy import (
    SqlAlchemyClientRepository,
    SqlAlchemySubmissionRepository,
)

router = APIRouter(prefix="/clients", tags=["clients"])
db_session_dependency = Depends(get_db_session)


@router.get("", response_model=list[ClientListItem])
async def list_clients(
    search: str | None = Query(default=None, max_length=255),
    session: AsyncSession = db_session_dependency,
) -> list[ClientListItem]:
    search_term = search.strip() if search else None
    clients = await SqlAlchemyClientRepository(session).list_summaries(search=search_term)
    return [
        ClientListItem(
            id=client.client.id,
            email_normalized=client.client.email_normalized,
            display_name=client.client.display_name,
            submission_count=client.submission_count,
        )
        for client in clients
    ]


@router.get("/{client_id}", response_model=ClientDetailResponse)
async def get_client(
    client_id: UUID,
    session: AsyncSession = db_session_dependency,
) -> ClientDetailResponse:
    client_repository = SqlAlchemyClientRepository(session)
    client = await client_repository.get_by_id(str(client_id))
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} was not found.",
        )

    submissions = await SqlAlchemySubmissionRepository(session).list_by_client_id(str(client_id))
    return ClientDetailResponse(
        id=UUID(client.id),
        email_normalized=client.email_normalized,
        display_name=client.display_name,
        submissions=[
            ClientSubmissionResponse(
                id=UUID(submission.id),
                source_type=submission.source_type,
                spreadsheet_id=submission.source_spreadsheet_id,
                sheet_name=submission.source_sheet_name,
                source_row_number=submission.source_row_number,
                source_row_hash=submission.source_row_hash,
                questionnaire_version=submission.questionnaire_version,
                submitted_at=submission.submitted_at,
                imported_at=submission.imported_at,
                raw_payload=dict(submission.raw_payload),
            )
            for submission in submissions
        ],
    )
