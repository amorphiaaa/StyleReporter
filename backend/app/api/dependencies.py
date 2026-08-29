from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.contracts import CanvaDesignProvider, ReportPlacementAgent


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_canva_provider(request: Request) -> CanvaDesignProvider:
    provider = getattr(request.app.state, "canva_provider", None)
    if provider is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Canva integration is not configured.",
        )
    return provider


def get_report_placement_agent(request: Request) -> ReportPlacementAgent | None:
    return getattr(request.app.state, "report_placement_agent", None)
