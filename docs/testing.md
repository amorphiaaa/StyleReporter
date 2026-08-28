# Scaffold verification

## Backend

```powershell
cd backend
uv sync --dev
uv run pytest
uv run ruff check .
```

Expected behavior:

- health tests pass;
- importer tests cover normalization, invalid email, and idempotency;
- questionnaire contract tests cover typed field mapping, image-link
  splitting, required fields, and unknown-version fallback;
- import history tests cover summary counters, detailed row errors, and
  provider-independent persistence;
- Google Sheets and Drive provider tests use injected fakes and never require
  credentials;
- contract tests run without external provider calls.

## Frontend

```powershell
cd frontend
pnpm install
pnpm lint
pnpm test
pnpm build
```

Expected behavior:

- the TypeScript project type-checks;
- the API client fallback points to localhost;
- the manual import screen submits a synthetic payload and renders counters;
- the Imports screen lists runs and opens persisted metadata and row errors;
- the clients screen lists profiles and opens submission and asset details;
- the production bundle builds.

## Compose smoke check

```powershell
docker compose up --build
```

Verify the API health URL and frontend URL from the root README. Stop with
`docker compose down` after the check.

For a persistence smoke test, POST synthetic rows to
`/api/v1/imports/manual`, then retrieve the returned ID from
`/api/v1/imports/{import_id}`. No text-generation endpoint is available in the
current application.
