# Handoff guide

This repository is ready for the next engineer to continue the first product
slice. The current commit contains a working Google Sheets importer, client
list/detail screens, structured report persistence, and a local Codex CLI
runtime behind a host-side worker.
The optional Google Drive publisher now creates the canonical per-client folder
tree, while the local workspace remains the Codex CLI cache.

## Read first

1. README.md
2. docs/architecture.md
3. docs/domain-model.md
4. docs/adr/
5. backend/app/domain/contracts.py
6. backend/tests/fixtures/sample_questionnaire_row.json

## Recommended implementation order

1. Add client deletion only after retention, audit, and report-history policy
   are agreed.
2. Configure and test the Google Sheets and Drive providers with a real service
   account, spreadsheet sharing, Drive-file access, and a controlled response
   sheet. Give the service account Editor access to the configured Drive root;
   keep `GOOGLE_DRIVE_STORAGE_ENABLED=false` and `ASSET_DOWNLOAD_ENABLED=false`
   until access is verified.
3. Review visual observations and generated reports against controlled
   questionnaire examples; keep `codex_cli` runs local and human-reviewed.
4. Add persistence/indexing for `submission_assets` if the UI needs searchable
   asset history beyond filesystem manifests.
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

The next engineer should be able to explain what is implemented, which gated
providers return 503 or 502, where each future integration belongs, and which
tests must be added for the first product slice.
