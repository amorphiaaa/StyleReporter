# StyleReporter

StyleReporter is a FastAPI + React application for importing client
questionnaires, preserving source evidence, and organizing client assets.

## Current stage: import and evidence workspace

The application currently supports Google Sheets/manual questionnaire import,
client persistence, local asset workspaces, and optional Google Drive
publishing. Questionnaire rows are stored as raw JSONB, while versioned
definitions provide a stable, provider-neutral mapping for identity and asset
fields.

Text/report generation is intentionally not part of the current application.
The previous Codex CLI, OpenAI, few-shot, methodologist, and Canva candidate
generation workflow has been removed while the replacement workflow is being
designed.

Not implemented:

- text or style report generation
- Canva candidate generation
- client deletion UI
- user authentication
- scheduled jobs or webhooks
- production deployment or CI/CD

## Repository layout

- `backend/` - FastAPI application, domain contracts, migrations, and tests
- `frontend/` - Vite/React/TypeScript client and import screens
- `infra/` - local Docker Compose support
- `docs/` - architecture, domain notes, ADRs, and handoff instructions

## Local startup

Requirements: Docker Desktop with Compose.

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Then open:

- API health: http://127.0.0.1:8001/health
- API docs: http://127.0.0.1:8001/docs
- Frontend: http://127.0.0.1:5174

To stop the stack:

```powershell
docker compose down
```

## Import and asset workflows

The manual import endpoint is available at
`POST http://127.0.0.1:8001/api/v1/imports/manual`. The read-only Google Sheets
endpoint is available at
`POST http://127.0.0.1:8001/api/v1/imports/google-sheets/sync`; it remains
disabled until `GOOGLE_SHEETS_ENABLED=true`, service-account credentials, and a
spreadsheet ID are supplied. Set `GOOGLE_QUESTIONNAIRE_VERSION` when a mapped
questionnaire definition should be applied during sync.

Recent import runs are available at
`GET http://127.0.0.1:8001/api/v1/imports?limit=20`. Select a run in the
Imports screen to load its source metadata and row-level errors from
`GET http://127.0.0.1:8001/api/v1/imports/{import_id}`.

When a mapping or source header changes after rows were imported, pass
`{"refresh_existing": true}` to the Google Sheets sync request to backfill
existing source rows without creating duplicate submissions.

Successful imports create a local client asset workspace under `var/assets`
(or `ASSET_STORAGE_ROOT`). Set `ASSET_DOWNLOAD_ENABLED=true` to download
questionnaire images. Existing submissions can be reprocessed with
`refresh_existing`.

To make Google Drive the canonical client workspace, set
`GOOGLE_DRIVE_STORAGE_ENABLED=true` and provide
`GOOGLE_DRIVE_ROOT_FOLDER_ID`. For a personal Drive, configure
`GOOGLE_DRIVE_OAUTH_CLIENT_JSON` and `GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN`.
Publishing is disabled by default.

Each imported client gets one stable folder:

```text
<configured root>/<client name> [<client id>]/
  Questionnaire/
  Good Outfits/
  Bad Outfits/
  Inspiration/
  Final Report/
```

The workspace and Drive integrations only handle preserved questionnaire data
and downloaded assets. They do not generate text or reports.

## Local development without Docker

Backend:

```powershell
cd backend
uv sync --dev
uv run uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
corepack enable
pnpm install
pnpm dev
```

## Handoff

Read `docs/handoff.md` before implementing the replacement workflow. New
provider-specific code should remain behind the contracts in
`backend/app/domain/contracts.py`.
