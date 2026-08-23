# Codex CLI, Agents SDK contract, and Canva boundary

The backend includes an Agents SDK boundary. The current
`agents_sdk_dry_run` path constructs a typed `Agent` with structured output and
returns a deterministic preview of the four-section Style Language analysis,
but does not call `Runner.run` or execute tools.

The real output contract is:

- `current_style_language`;
- `desired_style_language`;
- `disconnect`;
- `your_action_plan` with 3-5 prioritized actions, rationale, and first step.

The prompt is intentionally evidence-bound: missing answers remain unknown,
Image URLs without downloaded local attachments are treated as metadata, and
the agent must not invent client facts. Verified downloaded images may be
attached to the local Codex CLI runtime for direct visual observations.

The production local runtime uses the Codex CLI worker described in
`docs/codex-cli-runtime.md`. The Agents SDK dependency is retained only for a
typed, no-network contract preview; it is not used to make the report model
call.

The earlier Agents SDK references remain useful for the contract shape:

- Official OpenAI Agents documentation:
  https://developers.openai.com/api/docs/guides/agents
- Python SDK documentation:
  https://openai.github.io/openai-agents-python/

The `openai-agents` dependency is present and used by
`AgentsSdkStyleReportRuntime` only in `agents_sdk_dry_run`. The `codex_cli`
route delegates the actual model call to the locally authenticated CLI worker,
so it does not require `OPENAI_API_KEY`.

## Separate concepts

- CanvaSkill: domain capability description and future tool surface.
- CanvaConnector: transport/auth boundary for a future Canva OAuth or MCP
  integration.
- AgentRuntime: orchestration boundary that may register the skill later.
- AgentsSdkStyleReportRuntime: typed no-network contract preview.
- CodexCliStyleReportRuntime: HTTP client for the host-side Codex CLI worker.

The scaffold connector reports configured=false and performs no network
request. Canva credentials, OAuth flow, MCP endpoint, asset copying, and
export operations are intentionally deferred.

## Future safety rule

The agent may consume persisted questionnaire evidence. It must not make the
Google importer depend on Canva or OpenAI availability.
