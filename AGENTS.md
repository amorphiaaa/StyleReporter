# Instructions for future contributors

## Scope

The repository contains a product slice for Google import, persistence, and
client evidence workspaces. Text/report generation is intentionally removed;
do not reintroduce it or add new provider calls without a separate product
task.

## Boundaries

- Keep provider-specific code behind domain contracts.
- Keep raw questionnaire payloads as the source of truth.
- Do not commit credentials, client data, source ZIP files, or real image URLs.
- Do not make Google or other provider calls in unit tests.
- Prefer async interfaces in backend contracts.
- Keep API and frontend types aligned through the documented API contract.

## Verification

Backend:

    cd backend
    uv run pytest
    uv run ruff check .

Frontend:

    cd frontend
    pnpm lint
    pnpm test
    pnpm build

The scaffold must remain bootable with Docker Compose after changes.
