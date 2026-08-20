# StyleReporter

StyleReporter is a scaffold for a future FastAPI + React application that will
turn client questionnaire data into personalized style reports.

## Current stage: local report vertical slice

This repository contains the handoff scaffold, a manual import slice, and a
local report vertical slice. Already-read rows are persisted in PostgreSQL;
the client detail screen can launch a deterministic stub report for a saved
submission. The Google Sheets provider is present but disabled by default, so
the local stack still makes no external provider calls.

Not implemented:

- client deletion UI
- user authentication
- scheduled jobs or webhooks
- OpenAI model calls or production prompts (the Agents SDK dry-run adapter and
  local stub runtime are available)
- Canva connector/OAuth/MCP calls
- methodology-driven style report generation
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

The internal manual import endpoint is available at
`POST http://localhost:8000/api/v1/imports/manual`. It accepts synthetic or
already-read rows. The read-only Google Sheets endpoint is available at
`POST http://localhost:8000/api/v1/imports/google-sheets/sync`; it remains
disabled until `GOOGLE_SHEETS_ENABLED=true`, service-account credentials, and a
spreadsheet ID are supplied. Its provider is covered by offline mock tests;
no Google credentials are committed.

The local report endpoint is available at
`POST http://localhost:8000/api/v1/clients/{client_id}/reports`. Pass a saved
`submission_id` to generate a deterministic `stub-v1` response without an
OpenAI key. You can also pass `runtime: "agents_sdk_dry_run"` to verify that
the typed Agents SDK agent contract is constructed without calling a model. The
real `agents_sdk` runtime is disabled by default; requests receive `503` until
`OPENAI_AGENT_RUNTIME_ENABLED=true` and `OPENAI_API_KEY` are configured.
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
