# Handoff guide

This repository is ready for the next engineer to implement the first product
slice. The current commit is scaffolding, not a working importer.

## Read first

1. README.md
2. docs/architecture.md
3. docs/domain-model.md
4. docs/adr/
5. backend/app/domain/contracts.py
6. backend/tests/fixtures/sample_questionnaire_row.json

## Recommended implementation order

1. Add SQLAlchemy models and the first Alembic migration.
2. Add repository implementations and transaction boundaries.
3. Implement the read-only Google Sheets adapter.
4. Implement the questionnaire importer with idempotency and row errors.
5. Replace the 501 routes with typed API schemas.
6. Connect the frontend API client and import results screen.
7. Add the Agents SDK runtime only after persisted evidence is available.
8. Implement Canva through the documented connector boundary.

## Non-negotiable constraints

- Keep credentials out of git.
- Keep raw questionnaire answers intact.
- Do not diagnose or generate report prose during ingestion.
- Do not add real client data to fixtures.
- Keep provider calls out of unit tests.
- Do not remove explicit scaffold markers until the corresponding feature is
  actually implemented and tested.

## Handoff acceptance

The next engineer should be able to explain what is implemented, what returns
501, where each future integration belongs, and which tests must be added for
the first product slice.
