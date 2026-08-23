# StyleReporter

StyleReporter is a FastAPI + React application that imports client
questionnaires and can generate a local style report through Codex CLI.

## Current stage: local report vertical slice

This repository contains the handoff scaffold, a Google Sheets import slice,
and a local report vertical slice. Already-read rows are persisted in
PostgreSQL, and each successful submission creates a local client evidence
workspace under `var/assets` (or `ASSET_STORAGE_ROOT`). The client detail screen
can launch a deterministic preview or send one saved submission to a host-side
Codex CLI worker. The worker uses the local Codex CLI session rather than
`OPENAI_API_KEY`.

Questionnaires are normalized through versioned JSON definitions before identity
fields are imported. Source header aliases and report-required fields live in
`backend/app/domain/questionnaire_definitions/`, so a form label change does not
require changing importer code. Full source rows remain preserved as raw JSONB,
and unknown questionnaire versions stay raw-only until their mapping is
explicitly defined.

The current MVP report target is a single-questionnaire analysis with four
sections: `CURRENT STYLE LANGUAGE`, `DESIRED STYLE LANGUAGE`, `THE DISCONNECT`,
and `YOUR ACTION PLAN`. The Agents SDK dry-run remains as an offline contract
preview; the real local runtime uses `codex exec --output-schema` through the
companion worker.

Not implemented:

- client deletion UI
- user authentication
- scheduled jobs or webhooks
- unattended production scheduling and job retries for Codex CLI runs
- Canva connector/OAuth/MCP calls
- production methodology-driven style report generation
- production deployment or CI/CD

## Repository layout

- backend/ - FastAPI application, domain contracts, migration skeleton, tests
- frontend/ - Vite/React/TypeScript shell with import and client screens
- infra/ - local Docker Compose support
- docs/ - architecture, domain notes, ADRs, and handoff instructions

## Local startup

Requirements: Docker Desktop with Compose.

    Copy-Item .env.example .env
    docker compose up --build

Then open:

- API health: http://localhost:8000/health
- API docs: http://localhost:8000/docs
- Frontend: http://localhost:5173

For the real report runtime, authenticate Codex CLI once and start the local
worker in a second PowerShell window:

    codex login
    .\tools\run-codex-cli-worker.ps1

Check the worker before using the `Codex CLI (local)` option:

    Invoke-RestMethod http://localhost:8787/health

The worker is intentionally host-side because the saved Codex CLI session is
owned by Windows, not by the backend container. It binds a local development
endpoint and should not be exposed as a public service. See
`docs/codex-cli-runtime.md` for the token and troubleshooting options.

To download questionnaire images into the shared client workspace, set
`ASSET_DOWNLOAD_ENABLED=true` in `.env` and run a sync. The service account
must have access to the uploaded Drive files. Existing submissions can be
reprocessed with `{"refresh_existing": true}`. Only successfully downloaded
images are attached to subsequent local Codex CLI report runs.

To make Google Drive the canonical client workspace, also set
`GOOGLE_DRIVE_STORAGE_ENABLED=true` and provide `GOOGLE_DRIVE_ROOT_FOLDER_ID`.
The service account must have Editor access to that root folder. Each imported
client then gets one stable folder with this structure:

```text
<configured root>/<client name> [<client id>]/
  Questionnaire/
  Good Outfits/
  Bad Outfits/
  Inspiration/
  Final Report/
```

The five folders are created idempotently on import. `questionnaire.json` is
uploaded to `Questionnaire`; downloaded images are uploaded according to the
versioned questionnaire mapping. The local workspace remains a shared cache
for Codex CLI, and `Final Report` is reserved for the future report exporter.
Drive publishing is disabled by default and has no effect until the flag is
explicitly enabled.

The internal manual import endpoint is available at
`POST http://localhost:8000/api/v1/imports/manual`. It accepts synthetic or
already-read rows. The read-only Google Sheets endpoint is available at
`POST http://localhost:8000/api/v1/imports/google-sheets/sync`; it remains
disabled until `GOOGLE_SHEETS_ENABLED=true`, service-account credentials, and a
spreadsheet ID are supplied. Set `GOOGLE_QUESTIONNAIRE_VERSION` when a mapped
questionnaire definition should be applied during sync. Its provider is covered
by offline mock tests; no Google credentials are committed.

Recent runs are available at `GET http://localhost:8000/api/v1/imports?limit=20`;
the Imports screen displays their status and counters. Select a run there to
load its persisted source metadata and row-level errors from
`GET http://localhost:8000/api/v1/imports/{import_id}`.

When a mapping or source header changes after rows were imported, pass
`{"refresh_existing": true}` to the Google Sheets sync request to backfill the
existing source rows without creating duplicate submissions.

The local report endpoint is available at
`POST http://localhost:8000/api/v1/clients/{client_id}/reports`. Pass a saved
`submission_id` and `runtime: "codex_cli"` to generate a structured report
through the host worker without configuring an OpenAI API key. The
`agents_sdk_dry_run` runtime remains available for offline contract checks.
Runtime exceptions are saved as failed report runs and return `502`, so the
attempt remains visible in report history.
Retrieve the run later with
`GET http://localhost:8000/api/v1/reports/{report_run_id}`.

To stop the stack:

    docker compose down

## Local development without Docker

Backend:

    cd backend
    uv sync --dev
    uv run uvicorn app.main:app --reload

Frontend:

    cd frontend
    corepack enable
    pnpm install
    pnpm dev

## Handoff

Read docs/handoff.md before implementing the first product slice. The
scaffolding boundaries are intentional: new integrations should be added
behind the contracts in backend/app/domain/contracts.py.
