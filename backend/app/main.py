from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import clients, health, imports, reports
from app.core.config import get_settings
from app.db.session import create_session_factory


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="StyleReporter API",
        version="0.1.0",
        description="StyleReporter API with an internal questionnaire import slice.",
    )
    application.state.session_factory = create_session_factory()
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
    application.include_router(reports.router, prefix="/api/v1")
    return application


app = create_app()
