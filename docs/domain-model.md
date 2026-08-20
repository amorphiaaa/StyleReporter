# Domain model decisions

The supplied methodology materials describe a questionnaire with:

- current style answers;
- style self-perception;
- three "Feels Like Me" images;
- one "Not Me" image;
- three inspiration images;
- a selected visual world.

These are source fields, not yet a diagnosis schema.

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
provider metadata. No binary download or object storage is part of the
scaffold.

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
