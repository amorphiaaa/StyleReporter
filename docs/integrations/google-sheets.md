# Google Sheets integration boundary

Google Forms is treated as the upstream questionnaire authoring tool. The
initial adapter will read the linked response spreadsheet rather than making
the questionnaire importer responsible for form UI details.

The Google Sheets API exposes values by spreadsheet ID and A1 range through
the spreadsheets.values.get operation:

https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/get

## Configuration

- GOOGLE_SERVICE_ACCOUNT_JSON
- GOOGLE_SPREADSHEET_ID
- GOOGLE_SHEET_NAME
- GOOGLE_SHEET_RANGE (optional A1 range)
- GOOGLE_QUESTIONNAIRE_VERSION (optional versioned mapping)
- GOOGLE_SHEETS_ENABLED (false by default)
- GOOGLE_SHEETS_TIMEOUT_SECONDS
- an explicit email-column header

The response sheet must be shared with the service-account email. Credentials
must be injected through secrets or environment configuration and never stored
in the repository.

## Adapter contract

GoogleSheetsSource.read_rows(SheetReadRequest) returns rows mapped by the
header row. Unknown headers must be preserved. The adapter should be read-only.

## Import behavior contract

1. Read the configured sheet range.
2. Preserve all source headers and values in raw payload.
3. Resolve the configured questionnaire version and its header aliases.
4. Normalize the configured email value by trimming and case-folding it.
5. Reject blank or structurally invalid email values.
6. Upsert the client by normalized email.
7. Create the submission by source sheet and row identity.
8. Skip a source row that was already seen in the same run or repository.
9. Record invalid rows as structured import errors.

## Local implementation

`GoogleSheetsApiSource` reads `spreadsheets.values.get` through a read-only
transport and maps the first returned row to headers. Its service-account token
provider and HTTP transport are separate injectable boundaries, so provider
tests do not need credentials or network access. `FixtureGoogleSheetsSource`
provides deterministic `SheetRow` values for local tests.

`QuestionnaireImportService` consumes the `GoogleSheetsSource`,
`ClientRepository`, and `SubmissionRepository` contracts without knowing
whether they are backed by fixtures, PostgreSQL, or Google APIs. The
versioned questionnaire definitions in
`backend/app/domain/questionnaire_definitions/` resolve source headers into
stable internal keys and keep unknown columns in the raw payload.

The current fixture covers a new client, a repeat email, a missing email, and a
second client. It intentionally includes synthetic `example.test` image URLs
only.

`POST /api/v1/imports/google-sheets/sync` uses the same importer and PostgreSQL
transaction boundary as the manual endpoint. It returns `503` while
`GOOGLE_SHEETS_ENABLED=false` or credentials/configuration are missing, and
`502` for an upstream Google Sheets API failure. The endpoint is intentionally
not scheduled and has no webhook or background worker yet.
