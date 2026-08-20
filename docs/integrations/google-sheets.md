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

## Planned import behavior

1. Read the configured sheet range.
2. Preserve all source headers and values in raw payload.
3. Normalize the configured email value.
4. Upsert the client by normalized email.
5. Create or update the submission by source sheet and row identity.
6. Record missing-email rows as rejected import items.

No implementation or provider call belongs in the scaffold.
