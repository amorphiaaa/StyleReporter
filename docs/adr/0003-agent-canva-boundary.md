# ADR 0003: Keep Agents SDK and Canva behind independent boundaries

## Status

Accepted

## Decision

The future agent runtime, Canva skill, and Canva connector are separate
interfaces. The importer must not require OpenAI or Canva to store questionnaire
evidence.

## Consequences

The agent workflow can be introduced after ingestion is stable. Canva
authentication and transport can change without rewriting domain services.
