# Architecture scaffold

## Intent

This repository is a handoff-ready scaffold. The first implementation slice is
a local synthetic import pipeline; the provider adapter and database wiring are
still separate follow-up work.

## Components

- React frontend: navigation shell for clients and future import runs.
- FastAPI backend: health endpoint, placeholder routes, configuration, and
  domain contracts.
- PostgreSQL: included in Compose; the initial schema foundation is present,
  while repositories and API persistence wiring remain future work.
- Google Sheets adapter: provider stub plus a deterministic fixture source.
- Questionnaire importer: provider-agnostic service with validation,
  normalization, and source-row idempotency.
- Agents SDK runtime: future style-methodology workflow.
- Canva connector: future provider boundary for asset workflows.

## Intended future flow

Google Forms -> linked response Sheet -> GoogleSheetsSource ->
QuestionnaireImporter -> client/submission repositories -> future agent workflow.

The current tests exercise the same flow with FixtureGoogleSheetsSource and
in-memory repositories. No Google, database, or AI provider calls are made.

The importer and agent must remain separate. Importing a questionnaire stores
evidence; it does not diagnose the client.

## Current runtime behavior

- GET /health returns the scaffold status.
- Client and import routes return HTTP 501 with an explicit message.
- No external credentials are required.
- No database connection is opened during API startup.
