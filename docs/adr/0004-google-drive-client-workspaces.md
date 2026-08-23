# ADR 0004: Google Drive client workspaces

## Status

Accepted for the current product slice.

## Decision

Google Drive is the canonical human-facing workspace for imported client
evidence. A configured root folder contains one folder per client, with these
fixed children:

```text
Questionnaire
Good Outfits
Bad Outfits
Inspiration
Final Report
```

The importer creates the client folder and all five children idempotently. It
uses Drive `appProperties` keys based on client ID, submission ID, field key,
and ordinal instead of using display names as identity. The local filesystem
workspace remains the Codex CLI cache and the source for verified uploads.

## Consequences

- A service account needs Editor access to the configured root folder and the
  Drive write scope; the feature is disabled by default.
- `questionnaire.json` is uploaded immediately. Image files are uploaded only
  after the optional downloader has verified them locally.
- The `Final Report` folder is reserved for the later report exporter; this
  iteration does not upload reports.
- A failed Drive call rolls back the database import transaction. Any folders
  already created remain safe to reuse because retries use stable keys.
- Tests use `httpx.MockTransport`; no Google API calls or credentials are used
  in the test suite.
