# Scaffold verification

## Backend

    cd backend
    uv sync --dev
    uv run pytest
    uv run ruff check .

Expected behavior:

- health test passes;
- synthetic importer tests cover normalization, invalid email, and idempotency;
- questionnaire contract tests cover typed field mapping, image-link splitting,
  missing report fields, and unknown-version fallback;
- import history tests cover summary counters, detailed row errors, and the
  frontend history/detail queries;
- Google Sheets provider tests use injected token/HTTP fakes and never call
  Google or require credentials;
- report failure tests verify failed runs keep an error message for history;
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
- the Imports screen lists recent runs and opens persisted metadata and row
  errors for a selected run;
- the clients screen lists persisted profiles and opens a submission detail;
- the client detail loads report history, can launch a stub report, and renders
  structured output;
- the production bundle builds.

## Compose smoke check

    docker compose up --build

Verify the API health URL and frontend URL from the root README. Stop with
docker compose down after the check.

For a backend persistence smoke test, POST synthetic rows to
`/api/v1/imports/manual`, then retrieve the returned ID from
`/api/v1/imports/{import_id}`. The endpoint writes only synthetic data during
local verification. Then POST the returned client/submission IDs to
`/api/v1/clients/{client_id}/reports` and retrieve the generated run from
`/api/v1/reports/{report_run_id}`.
