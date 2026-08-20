# Scaffold verification

## Backend

    cd backend
    uv sync --dev
    uv run pytest
    uv run ruff check .

Expected behavior:

- health test passes;
- future import route returns HTTP 501;
- contract tests run without external provider calls.

## Frontend

    cd frontend
    pnpm install
    pnpm lint
    pnpm test
    pnpm build

Expected behavior:

- the TypeScript project type-checks;
- the API client fallback points to localhost;
- the production bundle builds.

## Compose smoke check

    docker compose up --build

Verify the API health URL and frontend URL from the root README. Stop with
docker compose down after the check.
