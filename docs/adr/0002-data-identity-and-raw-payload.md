# ADR 0002: Email identity and raw questionnaire payloads

## Status

Accepted for the future import slice

## Decision

Clients will be deduplicated by normalized email. Each questionnaire response
will remain a separate submission. The complete source row will be retained as
raw JSONB; only operational metadata and client identity are normalized.

## Consequences

Repeated questionnaires preserve history. Unknown future form columns do not
force an immediate schema change. Rows without email require an explicit
rejection path rather than unsafe name-based merging.
