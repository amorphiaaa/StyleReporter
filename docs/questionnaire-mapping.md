# Questionnaire mapping

Questionnaire source headers are configuration, not application logic. Versioned
definitions live in `backend/app/domain/questionnaire_definitions/*.json`.

Each definition contains:

- `version`: immutable identifier stored on each submission;
- `identity.email`: accepted source headers for client identity;
- `identity.display_name`: accepted source headers for the client label;
- `fields`: mappings from source headers to stable internal keys;
- `required`: whether the answer is required by the questionnaire mapping;
- `multiple` and `value_type`: how the value is normalized for downstream use.

## How to change a questionnaire

Use aliases when only a source header changes. For example, add `Your name` to
the `display_name` list without changing the internal field contract.

Create a new JSON definition when the questionnaire is materially changed:

1. copy the previous definition;
2. change `version`, for example from `client-style-v1` to `client-style-v2`;
3. add, remove, or rename source fields in the new definition;
4. set `GOOGLE_QUESTIONNAIRE_VERSION` to the selected version for future syncs.

Existing submissions retain their original raw payload and questionnaire version.
This keeps imported source rows stable while new responses use the new mapping.

When an existing sheet has already been imported, run a deliberate refresh to
apply a new mapping to those source rows without creating duplicate submissions:

```powershell
$syncBody = @{
  questionnaire_version = "fixture-v1"
  refresh_existing = $true
} | ConvertTo-Json
```

The refresh fills a missing client display name but does not overwrite a name
that was edited manually in the client profile.

Unknown source columns are always preserved in `raw_payload`. Mapped fields are
available through the normalized questionnaire object, so adding an optional
field to a definition does not require a database migration.

## Current definition

`fixture-v1` includes aliases for the current local form headers:

- `Email`, `Your email`, `Email Address`;
- `Name`, `Your name`.

The Google Sheets sync still requires a valid email. Rows without one remain
rejected because email is the client deduplication identity.
