# Architecture scaffold

## Intent

This repository is a handoff-ready scaffold. The first implementation slice
will be a manual Google Sheets import, but the current repository does not
perform that import.

## Components

- React frontend: navigation shell for clients and future import runs.
- FastAPI backend: health endpoint, placeholder routes, configuration, and
  domain contracts.
- PostgreSQL: included in Compose; the initial schema foundation is present,
  while repositories and persistence workflow remain future work.
- Google Sheets adapter: future read-only source provider.
- Questionnaire importer: future application service.
- Agents SDK runtime: future style-methodology workflow.
- Canva connector: future provider boundary for asset workflows.

## Intended future flow

Google Forms -> linked response Sheet -> GoogleSheetsSource ->
QuestionnaireImporter -> client/submission repositories -> future agent workflow.

The importer and agent must remain separate. Importing a questionnaire stores
evidence; it does not diagnose the client.

## Current runtime behavior

- GET /health returns the scaffold status.
- Client and import routes return HTTP 501 with an explicit message.
- No external credentials are required.
- No database connection is opened during API startup.
