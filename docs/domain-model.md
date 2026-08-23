# Domain model decisions

The supplied methodology materials describe a questionnaire with:

- current style answers;
- style self-perception;
- three "Feels Like Me" images;
- one "Not Me" image;
- three inspiration images;
- a selected visual world.

These are source fields, not yet a diagnosis schema.

## Questionnaire contract

`fixture-v1` has a typed normalization boundary driven by
`backend/app/domain/questionnaire_definitions/fixture-v1.json`. It maps source
headers and aliases into stable keys for future report and agent work: current
style, style goal, self-perception, style discomfort, image groups, and visual
world. New questionnaire versions are added as configuration files rather than
new hardcoded branches in the importer.

The importer still stores the complete original row as raw JSONB. Normalization
is additive and non-diagnostic: missing report fields are reported on the typed
object, but they do not discard otherwise valid source evidence. Unknown
questionnaire versions remain raw-only until an explicit mapping is added.
Mapped optional fields are available dynamically in the agent's
`normalized_answers` object without a database migration.

## Future persistence model

### clients

One client is identified by a normalized email. The normalized value is trimmed
and lowercased before a unique constraint is applied.

### questionnaire_submissions

Each form response is a separate submission linked to a client. The complete
source row is stored as raw JSONB so new questionnaire columns do not require an
immediate migration.

Operational metadata should include source provider, spreadsheet ID, sheet name,
source row number, row hash, questionnaire version, and timestamps.

### submission_assets

Future image references may be indexed separately with role, URL, filename, and
provider metadata. The current local asset workspace stores these references in
a per-client filesystem manifest and can optionally download supported image
files through the configured provider adapter. Object storage is still not
implemented.

### Local client workspace

When asset storage is enabled, each successful submission creates:

```text
<ASSET_STORAGE_ROOT>/clients/<client_id>/
  client.json
  submissions/<submission_id>/
    questionnaire.json
    manifest.json
    images/<questionnaire_field_key>/
```

`questionnaire.json` contains the preserved source row and import metadata.
`manifest.json` records image role, ordinal, source URL, download status,
content type, size, checksum, and local path when a download succeeds. Client
and submission IDs, rather than names or emails, are used in paths to avoid
unsafe path characters and accidental identity collisions.

Downloads are disabled by default. When enabled, direct HTTP(S) image URLs are
validated by content type and size, while common Google Drive file links are
read with the service-account Drive scope. Failed downloads remain visible in
the manifest and do not reject the questionnaire submission.

### Canonical Google Drive workspace

When `GOOGLE_DRIVE_STORAGE_ENABLED=true`, the importer publishes the local
submission workspace under the configured `GOOGLE_DRIVE_ROOT_FOLDER_ID`. The
service account must have Editor access to that root folder. Stable
`appProperties` keys, rather than display names, make retries idempotent:

```text
<root>/<client display name> [<client_id>]/
  Questionnaire/
  Good Outfits/
  Bad Outfits/
  Inspiration/
  Final Report/
```

`questionnaire.json` is stored in `Questionnaire`. Downloaded image files are
published to the folder declared by the versioned questionnaire definition:
the first `Feels Like Me` image (portrait) and body-proportion photo go to
`Questionnaire`, remaining `Feels Like Me` images go to `Good Outfits`, and
the `Not Me` and `Inspiration` groups go to their matching folders. The local
workspace remains the Codex CLI cache. `Final Report` is created now but is
reserved for a later report exporter.

### import_runs

Future manual syncs should create an auditable run record with status, counts,
timestamps, and row-level errors.

### style_report_runs

Each report run links one client to one questionnaire submission and records
runtime type, report version, status, timestamps, optional error text, and
structured JSONB output. Multiple runs for the same submission are allowed so
future runtimes can be retried or compared without overwriting questionnaire
evidence.

## Important boundary

Raw answers are evidence. Style Language categories, competing identities,
visual mistranslations, hypotheses, and final diagnoses belong to a later
agent/report domain and must not be inferred during ingestion.

The current `StubStyleReportRuntime` only exposes source field names and an
explicit placeholder message. It is not a methodology diagnosis.

## Import prototype rules

The local importer trims and case-folds email values for client identity while
preserving the original row unchanged in `raw_payload`. Invalid email rows are
rejected with a row-level error. Source spreadsheet ID, sheet name, and row
number form the idempotency key for a submission.

The client profile editor may update `display_name` only. The normalized email
is the deduplication identity and raw questionnaire answers are retained as
source evidence, so neither is editable from the profile UI.
