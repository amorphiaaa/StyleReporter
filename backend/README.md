# Backend import and evidence workspace

The backend exposes health, import, client, asset, manual report, and Canva
Autofill endpoints.

Canva is disabled by default. To enable report creation, set
`CANVA_ENABLED=true` and `CANVA_TEMPLATE_ID` to the Canva design ID. OAuth
credentials or a pre-issued access token can be used for Canva authentication.
Set `CANVA_SOURCE_TYPE=brand_template` when using a Canva Brand Template ID.
The API fetches the live dataset, uses an optional AI placement agent to map
user-authored text and image groups, uploads the selected assets, creates the
design, and optionally exports a PDF. The agent never generates or rewrites
report text.
It persists already-read questionnaire rows and keeps the complete raw payload
as the source of truth. Manual report content is saved per questionnaire
submission.

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

The import path preserves source evidence and does not diagnose a client.
