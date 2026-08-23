# Architecture scaffold

## Intent

This repository is a handoff-ready scaffold with a manual import slice and a
local report vertical slice. Provider adapters remain separate, while the
internal endpoints wire persisted evidence to PostgreSQL repositories.

## Components

- React frontend: navigation shell with manual import/history/detail and client
  list/detail screens.
- FastAPI backend: health endpoint, manual import API, client list/detail API,
  local style report API, configuration, and domain contracts.
- PostgreSQL: included in Compose; the initial schema foundation is present,
  with SQLAlchemy repositories and import-run persistence for the manual API.
- Google Sheets adapter: read-only REST provider with service-account auth and
  deterministic fixture source, behind a disabled-by-default feature flag.
- Questionnaire importer: provider-agnostic service with validation,
  normalization, and source-row idempotency.
- Questionnaire contract: versioned normalization for the known synthetic
  questionnaire; unknown versions remain raw-only.
- Asset workspace: local per-client folders with preserved questionnaire JSON,
  image-role directories, and a manifest of source URLs. Optional direct HTTP
  and Google Drive downloaders populate verified local image files.
- Style report runtime: deterministic stub, Agents SDK dry-run adapter, and a
  Codex CLI adapter. The real local path sends a structured prompt to the
  host-side companion worker, which invokes `codex exec` with read-only
  sandboxing and an output schema.
- Canva connector: future provider boundary for asset workflows.

## Intended future flow

Google Forms -> linked response Sheet -> GoogleSheetsSource ->
QuestionnaireImporter -> client/submission repositories + asset workspace ->
StyleReportRuntime -> report run persistence.

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
- GET /api/v1/imports?limit=... returns recent import-run summaries for the
  operator UI; GET /api/v1/imports/{import_id} remains the detailed run view.
- GET /api/v1/imports/{import_id} returns persisted run metadata.
- The Imports screen uses the detail endpoint to show source metadata, counters,
  and persisted row-level errors for a selected run.
- `fixture-v1` rows are normalized into a typed questionnaire context before
  identity fields are imported; raw answers remain unchanged.
- Successful imports create a local asset workspace under `ASSET_STORAGE_ROOT`
  with `client.json`, `questionnaire.json`, `manifest.json`, and role-based
  image directories. With `ASSET_DOWNLOAD_ENABLED=true`, successful downloads
  are recorded with a checksum and become eligible for local visual analysis.
- GET /api/v1/clients returns persisted client summaries.
- GET /api/v1/clients?search=... filters summaries by display name or
  normalized email.
- GET /api/v1/clients/{client_id} returns the client and raw submissions.
- PATCH /api/v1/clients/{client_id} updates only the display name; normalized
  email identity and raw submissions remain immutable through this UI.
- POST /api/v1/clients/{client_id}/reports generates a local `stub-v1` report
  for a persisted submission or a `codex-cli-v1` report through the local
  worker when `runtime: "codex_cli"` is selected.
- Runtime failures are persisted as `failed` report runs with an error message;
  the generation endpoint returns `502` while report history remains available.
- The same endpoint accepts `runtime: "agents_sdk_dry_run"` to construct the
  typed agent contract without a model call.
- `runtime: "codex_cli"` returns `503` with an actionable message when the
  local worker is disabled, not configured, or unavailable.
- The client detail UI exposes the deterministic preview, Agents SDK contract
  preview, and Codex CLI (local) runtime, with Codex CLI selected by default.
- The analysis UI renders current style language, desired style language, the
  disconnect, and a prioritized action plan when that structured output exists.
- GET /api/v1/reports/{report_run_id} returns a persisted report run.
- GET /api/v1/clients/{client_id}/reports returns report-run history ordered
  from newest to oldest.
- The import stack needs Google credentials only for live Sheets sync. The
  report stack uses the user's host-side Codex CLI session and does not need an
  OpenAI API key.
- The database engine is created at startup, but connections are opened only
  when an API request obtains a session.
