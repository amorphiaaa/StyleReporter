from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: str = "http://127.0.0.1:5174,http://localhost:5174"
    database_url: str = "postgresql+asyncpg://styler:styler@localhost:5432/stylereporter"

    google_service_account_json: str | None = None
    google_spreadsheet_id: str | None = None
    google_sheet_name: str = "Form Responses 1"
    google_sheet_range: str | None = None
    google_questionnaire_version: str | None = None
    google_refresh_existing: bool = False
    google_sheets_enabled: bool = False
    google_sheets_timeout_seconds: float = 10.0

    asset_storage_enabled: bool = True
    asset_storage_root: Path = Path("var/assets")
    asset_download_enabled: bool = False
    asset_download_timeout_seconds: float = 30.0
    asset_download_max_bytes: int = 20 * 1024 * 1024
    google_drive_storage_enabled: bool = False
    google_drive_root_folder_id: str | None = None
    google_drive_timeout_seconds: float = 30.0
    google_drive_oauth_client_json: str | None = Field(default=None, repr=False)
    google_drive_oauth_refresh_token: str | None = Field(default=None, repr=False)

    canva_enabled: bool = False
    canva_api_base_url: str = "https://api.canva.com/rest/v1"
    canva_client_id: str | None = None
    canva_client_secret: str | None = Field(default=None, repr=False)
    canva_redirect_uri: str = "http://127.0.0.1:8001/api/v1/canva/oauth/callback"
    canva_scopes: str = (
        "asset:read asset:write design:content:read design:content:write design:meta:read"
    )
    canva_access_token: str | None = Field(default=None, repr=False)
    canva_template_id: str | None = None
    canva_source_type: Literal["design", "brand_template"] = "design"
    canva_timeout_seconds: float = 60.0
    canva_poll_interval_seconds: float = 1.0
    canva_poll_attempts: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
