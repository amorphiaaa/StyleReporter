# Architecture scaffold

## Intent

This repository is a handoff-ready scaffold with a manual import slice. The
provider adapter remains separate, while the internal endpoint already wires
the importer to PostgreSQL repositories.

## Components

- React frontend: navigation shell for clients and future import runs.
- FastAPI backend: health endpoint, placeholder routes, configuration, and
  domain contracts.
- PostgreSQL: included in Compose; the initial schema foundation is present,
  with SQLAlchemy repositories and import-run persistence for the manual API.
- Google Sheets adapter: provider stub plus a deterministic fixture source.
- Questionnaire importer: provider-agnostic service with validation,
  normalization, and source-row idempotency.
- Agents SDK runtime: future style-methodology workflow.
- Canva connector: future provider boundary for asset workflows.

## Intended future flow

Google Forms -> linked response Sheet -> GoogleSheetsSource ->
QuestionnaireImporter -> client/submission repositories -> future agent workflow.

The unit tests exercise the same flow with FixtureGoogleSheetsSource and
in-memory repositories. The Compose smoke test exercises the manual endpoint
against PostgreSQL. No Google or AI provider calls are made.

The importer and agent must remain separate. Importing a questionnaire stores
evidence; it does not diagnose the client.

## Current runtime behavior

- GET /health returns the scaffold status.
- POST /api/v1/imports/manual persists already-read rows and returns import
  counters and row errors.
- GET /api/v1/imports/{import_id} returns persisted run metadata.
- Client routes remain HTTP 501 placeholders.
- No external credentials are required.
- The database engine is created at startup, but connections are opened only
  when an API request obtains a session.
