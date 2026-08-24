import asyncio
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.api.schemas.clients import (
    ClientAssetResponse,
    ClientDetailResponse,
    ClientListItem,
    ClientSubmissionResponse,
    ClientUpdateResponse,
    UpdateClientRequest,
)
from app.core.config import get_settings
from app.domain.contracts import ClientRecord
from app.repositories.sqlalchemy import (
    SqlAlchemyClientRepository,
    SqlAlchemySubmissionRepository,
)
from app.services.client_assets import find_downloaded_asset, list_downloaded_assets

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
    assets = await asyncio.to_thread(
        list_downloaded_assets,
        get_settings().asset_storage_root,
        str(client_id),
    )
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
        assets=[
            ClientAssetResponse(
                submission_id=UUID(asset.submission_id),
                field_key=asset.field_key,
                ordinal=asset.ordinal,
                folder_key=asset.folder_key,
                folder_label=asset.folder_label,
                filename=asset.filename,
                content_type=asset.content_type,
                url=(
                    f"/api/v1/clients/{client_id}/assets/"
                    f"{quote(asset.submission_id, safe='')}/"
                    f"{quote(asset.field_key, safe='')}/{asset.ordinal}"
                ),
            )
            for asset in assets
        ],
    )


@router.get(
    "/{client_id}/assets/{submission_id}/{field_key}/{ordinal}",
    response_class=FileResponse,
    include_in_schema=False,
)
async def get_client_asset(
    client_id: UUID,
    submission_id: UUID,
    field_key: str,
    ordinal: int,
) -> FileResponse:
    asset = await asyncio.to_thread(
        find_downloaded_asset,
        get_settings().asset_storage_root,
        client_id=str(client_id),
        submission_id=str(submission_id),
        field_key=field_key,
        ordinal=ordinal,
    )
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset was not found.")
    return FileResponse(asset.path, media_type=asset.content_type, filename=asset.filename)


@router.patch("/{client_id}", response_model=ClientUpdateResponse)
async def update_client(
    client_id: UUID,
    payload: UpdateClientRequest,
    session: AsyncSession = db_session_dependency,
) -> ClientUpdateResponse:
    repository = SqlAlchemyClientRepository(session)
    client = await repository.get_by_id(str(client_id))
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} was not found.",
        )

    updated_client = ClientRecord(
        id=client.id,
        email_normalized=client.email_normalized,
        display_name=payload.display_name,
    )
    try:
        saved_client = await repository.save(updated_client)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return ClientUpdateResponse(
        id=UUID(saved_client.id),
        email_normalized=saved_client.email_normalized,
        display_name=saved_client.display_name,
    )
