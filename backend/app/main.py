from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import canva_reports, clients, health, imports, manual_reports
from app.core.config import get_settings
from app.db.session import create_session_factory
from app.integrations.canva_connect import CanvaConnectProvider


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="StyleReporter API",
        version="0.1.0",
        description="StyleReporter API with an internal questionnaire import slice.",
    )
    application.state.session_factory = create_session_factory()
    application.state.canva_provider = (
        CanvaConnectProvider(
            access_token=settings.canva_access_token,
            base_url=settings.canva_api_base_url,
            timeout_seconds=settings.canva_timeout_seconds,
            poll_interval_seconds=settings.canva_poll_interval_seconds,
            poll_attempts=settings.canva_poll_attempts,
        )
        if settings.canva_enabled and settings.canva_access_token
        else None
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health.router)
    application.include_router(clients.router, prefix="/api/v1")
    application.include_router(imports.router, prefix="/api/v1")
    application.include_router(manual_reports.router, prefix="/api/v1")
    application.include_router(canva_reports.router, prefix="/api/v1")
    return application


app = create_app()
