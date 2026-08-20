# Google Sheets integration boundary

Google Forms is treated as the upstream questionnaire authoring tool. The
initial adapter will read the linked response spreadsheet rather than making
the questionnaire importer responsible for form UI details.

The Google Sheets API exposes values by spreadsheet ID and A1 range through
the spreadsheets.values.get operation:

https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/get

## Planned configuration

- GOOGLE_SERVICE_ACCOUNT_JSON
- GOOGLE_SPREADSHEET_ID
- GOOGLE_SHEET_NAME
- an explicit email-column header

The response sheet must be shared with the service-account email. Credentials
must be injected through secrets or environment configuration and never stored
in the repository.

## Planned adapter contract

GoogleSheetsSource.read_rows(SheetReadRequest) returns rows mapped by the
header row. Unknown headers must be preserved. The adapter should be read-only.

## Import behavior contract

1. Read the configured sheet range.
2. Preserve all source headers and values in raw payload.
3. Normalize the configured email value by trimming and case-folding it.
4. Reject blank or structurally invalid email values.
5. Upsert the client by normalized email.
6. Create the submission by source sheet and row identity.
7. Skip a source row that was already seen in the same run or repository.
8. Record invalid rows as structured import errors.

## Local implementation

`FixtureGoogleSheetsSource` provides deterministic `SheetRow` values for local
tests. `QuestionnaireImportService` consumes the `GoogleSheetsSource`,
`ClientRepository`, and `SubmissionRepository` contracts without knowing
whether they are backed by fixtures, PostgreSQL, or Google APIs.

The current fixture covers a new client, a repeat email, a missing email, and a
second client. It intentionally includes synthetic `example.test` image URLs
only.

The real Google Sheets adapter still requires credentials and is not
implemented. Until it is available, `POST /api/v1/imports/manual` accepts
already-read rows and sends them through the same importer and PostgreSQL
repositories.
