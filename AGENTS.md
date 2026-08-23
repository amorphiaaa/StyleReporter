# Instructions for future contributors

## Scope

The repository began as scaffolding and now contains a product slice for
Google import, persistence, and local Codex CLI report generation. Do not add
new provider calls or broaden the workflow without a separate product task.

## Boundaries

- Keep provider-specific code behind domain contracts.
- Keep raw questionnaire payloads as the source of truth.
- Do not commit credentials, client data, source ZIP files, or real image URLs.
- Do not make OpenAI, Codex CLI, Google, or Canva calls in unit tests.
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
