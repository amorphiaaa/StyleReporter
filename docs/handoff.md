# Handoff guide

This repository currently contains a working questionnaire importer, client
list/detail screens, local asset workspaces, and optional Google Drive
publishing. The previous text-generation and report-generation workflow has
been removed. The replacement workflow should be introduced as a separate
product slice.

## Read first

1. `README.md`
2. `docs/architecture.md`
3. `docs/domain-model.md`
4. `docs/adr/`
5. `backend/app/domain/contracts.py`
6. `backend/tests/fixtures/sample_questionnaire_row.json`

## Recommended implementation order

1. Agree on the replacement workflow and its source-of-truth boundaries.
2. Configure and test Google Sheets and Drive providers with controlled
   synthetic data. Keep provider flags disabled until access is verified.
3. Add persistence only when the replacement workflow has an approved data
   model.
4. Keep any new provider integration behind a domain contract and out of unit
   tests.

## Non-negotiable constraints

- Keep credentials out of git.
- Keep raw questionnaire answers intact.
- Do not diagnose the client during ingestion.
- Do not add real client data to fixtures.
- Keep provider calls out of unit tests.
- Do not reintroduce text generation without a separate product task.
