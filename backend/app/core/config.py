from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: str = "http://localhost:5173"
    database_url: str = "postgresql+asyncpg://styler:styler@localhost:5432/stylereporter"

    google_service_account_json: str | None = None
    google_spreadsheet_id: str | None = None
    google_sheet_name: str = "Form Responses 1"

    openai_api_key: str | None = Field(default=None, repr=False)
    openai_model: str | None = None
    openai_agent_runtime_enabled: bool = False

    canva_connector_url: str | None = None
    canva_client_id: str | None = Field(default=None, repr=False)
    canva_client_secret: str | None = Field(default=None, repr=False)

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
