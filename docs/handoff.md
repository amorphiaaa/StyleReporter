# Handoff guide

This repository is ready for the next engineer to continue the first product
slice. The current commit contains a working manual importer, a read-only
Google Sheets provider behind a disabled-by-default flag, client list/detail
screens, and a deterministic local report runtime. The real OpenAI provider is
still gated.

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
2. Review credentials, prompts, structured output validation, and tracing policy,
   then enable the gated real `AgentsSdkStyleReportRuntime` path with
   `OPENAI_AGENT_RUNTIME_ENABLED=true` and test it against a controlled model
   environment.
3. Configure and test the Google Sheets provider with a real service account,
   spreadsheet sharing, and a controlled response sheet.
4. Implement Canva through the documented connector boundary.

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
