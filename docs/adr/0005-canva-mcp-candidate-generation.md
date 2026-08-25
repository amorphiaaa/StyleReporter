# ADR 0005: Use host-side Canva MCP for candidate generation

## Status

Accepted for the MVP design stage.

## Decision

The application delegates Canva candidate generation to the same host-side
Codex CLI worker that already runs the local methodologist. The FastAPI
container never receives Canva credentials and never calls a Canva SDK
directly.

The workflow is deliberately split:

1. generate and persist the structured Style Language report;
2. ask Canva MCP for presentation candidates from that completed report;
3. show candidate links to the operator;
4. add final candidate selection, editable-design creation, and export in a
   later iteration.

## Rationale

- The user's local Codex authentication and Canva plugin live on the host, not
  in Docker.
- Canva is a design system, not the methodologist. Keeping it downstream
  prevents visual generation from changing the diagnosis.
- Candidate generation allows a human to compare visual directions before a
  persistent editable design is created.
- A Canva outage cannot block Google Sheets import or report persistence.

## Consequences

- The host must install and authenticate `canva@openai-curated` in the Codex
  profile used by the worker.
- `CANVA_MCP_ENABLED=true` is an explicit opt-in.
- Private Drive URLs may not be uploadable by Canva; the response must expose
  that limitation instead of pretending the images were included.
- Unit tests mock the worker transport and never call Canva.
