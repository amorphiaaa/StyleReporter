# Architecture scaffold

## Intent

This repository currently provides import, client-evidence, and user-authored
style report workflows. Provider adapters remain separate, while internal
endpoints persist source data and manual report content through PostgreSQL
repositories. Automatic report copy generation is outside the application. A
separately configured placement agent may classify user-authored text and
images for a Canva template, but it must not invent or rewrite report content.

## Components

- React frontend: navigation shell with import/history and client list/detail
  screens.
- FastAPI backend: health, import, client, and asset APIs.
- PostgreSQL: included in Compose with SQLAlchemy repositories and import-run
  persistence.
- Google Sheets adapter: read-only provider with service-account auth and a
  deterministic fixture source, behind a disabled-by-default feature flag.
- Questionnaire importer: provider-agnostic service with validation,
  normalization, and source-row idempotency.
- Questionnaire contract: versioned normalization for known questionnaires;
  unknown versions remain raw-only.
- Asset workspace: local per-client folders with preserved questionnaire JSON,
  image-role directories, and a manifest of source URLs. Optional downloaders
  populate verified local image files.
- Google Drive workspace publisher: optional provider that creates a stable
  client folder and publishes questionnaire data and verified images.
- Manual style report editor: React form for pasting the complete supplied
  report, organizing image groups, previewing the draft, and saving content per
  questionnaire submission.
- Canva placement agent: optional provider boundary that maps the user's
  existing text and image groups to opaque Canva fields.

## Intended current flow

Google Forms -> linked response Sheet -> GoogleSheetsSource ->
QuestionnaireImporter -> client/submission repositories + local asset workspace
-> optional Google Drive workspace publisher.

Importing a questionnaire stores evidence and makes a submission available for
manual report authoring. The default local stack makes no Google, AI, or Canva
provider calls. AI placement is opt-in through `OPENAI_API_KEY` and only runs
when a Canva report is created.

## Current runtime behavior

- `GET /health` returns the scaffold status.
- `POST /api/v1/imports/manual` persists already-read rows and returns import
  counters and row errors.
- `POST /api/v1/imports/google-sheets/sync` reads a configured sheet through the
  provider boundary and sends rows through the same importer transaction.
- `GET /api/v1/imports?limit=...` returns recent import-run summaries.
- `GET /api/v1/imports/{import_id}` returns persisted run metadata and row
  errors.
- `GET /api/v1/clients` returns persisted client summaries.
- `GET /api/v1/clients/{client_id}` returns the client, raw submissions, and
  downloaded assets.
- `GET /api/v1/clients/{client_id}/assets/...` serves a verified local asset.
- `PATCH /api/v1/clients/{client_id}` updates only the display name.
- `GET /api/v1/clients/{client_id}/submissions/{submission_id}/manual-report`
  loads the user's structured report draft.
- `PUT /api/v1/clients/{client_id}/submissions/{submission_id}/manual-report`
  creates or updates the user's structured report draft.

The database engine is created at startup, but connections are opened only
when an API request obtains a session. The default local stack makes no Google
or AI provider calls.
