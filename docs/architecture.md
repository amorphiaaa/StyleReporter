# Architecture scaffold

## Intent

This repository is a handoff-ready scaffold with a manual import slice and a
local report vertical slice. Provider adapters remain separate, while the
internal endpoints wire persisted evidence to PostgreSQL repositories.

## Components

- React frontend: navigation shell with manual import and client list/detail
  screens.
- FastAPI backend: health endpoint, manual import API, client list/detail API,
  local style report API, configuration, and domain contracts.
- PostgreSQL: included in Compose; the initial schema foundation is present,
  with SQLAlchemy repositories and import-run persistence for the manual API.
- Google Sheets adapter: read-only REST provider with service-account auth and
  deterministic fixture source, behind a disabled-by-default feature flag.
- Questionnaire importer: provider-agnostic service with validation,
  normalization, and source-row idempotency.
- Style report runtime: deterministic stub plus an Agents SDK dry-run adapter;
  real Runner calls remain behind the same runtime contract and a disabled-by-
  default feature flag.
- Canva connector: future provider boundary for asset workflows.

## Intended future flow

Google Forms -> linked response Sheet -> GoogleSheetsSource ->
QuestionnaireImporter -> client/submission repositories -> StyleReportRuntime ->
report run persistence.

The unit tests exercise the same flow with FixtureGoogleSheetsSource and
in-memory repositories. The Compose smoke test exercises the manual endpoint
against PostgreSQL. The default local stack makes no Google or AI provider
calls.

The importer and agent must remain separate. Importing a questionnaire stores
evidence; it does not diagnose the client.

## Current runtime behavior

- GET /health returns the scaffold status.
- POST /api/v1/imports/manual persists already-read rows and returns import
  counters and row errors.
- POST /api/v1/imports/google-sheets/sync reads a configured sheet through the
  provider boundary and sends rows through the same importer transaction.
- GET /api/v1/imports/{import_id} returns persisted run metadata.
- GET /api/v1/clients returns persisted client summaries.
- GET /api/v1/clients?search=... filters summaries by display name or
  normalized email.
- GET /api/v1/clients/{client_id} returns the client and raw submissions.
- PATCH /api/v1/clients/{client_id} updates only the display name; normalized
  email identity and raw submissions remain immutable through this UI.
- POST /api/v1/clients/{client_id}/reports generates a local `stub-v1` report
  for a persisted submission.
- Runtime failures are persisted as `failed` report runs with an error message;
  the generation endpoint returns `502` while report history remains available.
- The same endpoint accepts `runtime: "agents_sdk_dry_run"` to construct the
  typed agent contract without a model call.
- `runtime: "agents_sdk"` is accepted by the API but returns `503` until
  `OPENAI_AGENT_RUNTIME_ENABLED=true` and `OPENAI_API_KEY` are configured.
- The client detail UI exposes both local runtime choices and keeps `stub` as
  the default.
- GET /api/v1/reports/{report_run_id} returns a persisted report run.
- GET /api/v1/clients/{client_id}/reports returns report-run history ordered
  from newest to oldest.
- No external credentials are required.
- The database engine is created at startup, but connections are opened only
  when an API request obtains a session.
