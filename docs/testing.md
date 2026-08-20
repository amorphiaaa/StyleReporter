# Scaffold verification

## Backend

    cd backend
    uv sync --dev
    uv run pytest
    uv run ruff check .

Expected behavior:

- health test passes;
- synthetic importer tests cover normalization, invalid email, and idempotency;
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
- the manual import screen can submit a synthetic payload and render counters;
- the production bundle builds.

## Compose smoke check

    docker compose up --build

Verify the API health URL and frontend URL from the root README. Stop with
docker compose down after the check.

For a backend persistence smoke test, POST synthetic rows to
`/api/v1/imports/manual`, then retrieve the returned ID from
`/api/v1/imports/{import_id}`. The endpoint writes only synthetic data during
local verification.
