# Handoff guide

This repository is ready for the next engineer to continue the first product
slice. The current commit contains a working manual importer, client
list/detail screens, and a deterministic local report runtime, but not the
real Google or OpenAI providers.

## Read first

1. README.md
2. docs/architecture.md
3. docs/domain-model.md
4. docs/adr/
5. backend/app/domain/contracts.py
6. backend/tests/fixtures/sample_questionnaire_row.json

## Recommended implementation order

1. Add report-run list/history to the client detail screen.
2. Add client editing and search once the read-only client screens are stable.
3. Replace `StubStyleReportRuntime` with a tested Agents SDK runtime.
4. Implement the read-only Google Sheets adapter and connect it to the
   existing importer transaction boundary.
5. Implement Canva through the documented connector boundary.

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
