# Backend import and evidence workspace

The backend exposes health, import, client, and asset endpoints. It persists
already-read questionnaire rows and keeps the complete raw payload as the
source of truth. Text/report generation is currently removed; a replacement
workflow will be added in a separate product task.

## Commands

```powershell
uv sync --dev
uv run uvicorn app.main:app --reload
uv run pytest
uv run ruff check .
```

## Implementation boundaries

- Google Sheets adapter and auth/transport boundary: `app/integrations/google_sheets.py`
- Questionnaire orchestration: `app/services/questionnaire_importer.py`
- Local assets: `app/services/asset_workspace.py` and `app/services/client_assets.py`
- Google Drive storage: `app/integrations/google_drive_storage.py`
- Questionnaire mappings: `app/domain/questionnaire_definitions/`
- Repositories: `app/repositories/`

The import path must not call a text-generation provider or diagnose a client.
