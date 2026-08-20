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

## Important boundary

Raw answers are evidence. Style Language categories, competing identities,
visual mistranslations, hypotheses, and final diagnoses belong to a later
agent/report domain and must not be inferred during ingestion.

## Import prototype rules

The local importer trims and case-folds email values for client identity while
preserving the original row unchanged in `raw_payload`. Invalid email rows are
rejected with a row-level error. Source spreadsheet ID, sheet name, and row
number form the idempotency key for a submission.
