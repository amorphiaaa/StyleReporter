# StyleReporter

StyleReporter is a scaffold for a future FastAPI + React application that will
turn client questionnaire data into personalized style reports.

## Current stage: manual import slice

This repository contains the handoff scaffold plus a manual import slice. The
slice accepts already-read rows, persists clients, submissions, and import run
metadata in PostgreSQL, and exercises normalization, validation, raw payload
preservation, and source-row idempotency without calling external providers.

Not implemented:

- Google Sheets/Forms API integration
- frontend import workflow
- user authentication
- scheduled jobs or webhooks
- OpenAI agent execution or prompts
- Canva connector/OAuth/MCP calls
- style report generation
- production deployment or CI/CD

## Repository layout

- backend/ - FastAPI application, domain contracts, migration skeleton, tests
- frontend/ - Vite/React/TypeScript shell with placeholder pages
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
already-read rows until the real Google Sheets adapter is implemented.

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
