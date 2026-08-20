# Agents SDK and Canva boundary

The backend includes an Agents SDK boundary. The current
`agents_sdk_dry_run` path constructs a typed `Agent` with structured output but
does not call `Runner.run`, load production prompts, or execute tools.

The planned runtime will use the Python Agents SDK:

- Official OpenAI Agents documentation:
  https://developers.openai.com/api/docs/guides/agents
- Python SDK documentation:
  https://openai.github.io/openai-agents-python/

The `openai-agents` dependency is present and used by
`AgentsSdkStyleReportRuntime`. Model calls remain disabled until a later
iteration explicitly enables the real runtime with credentials and prompts.

## Separate concepts

- CanvaSkill: domain capability description and future tool surface.
- CanvaConnector: transport/auth boundary for a future Canva OAuth or MCP
  integration.
- AgentRuntime: orchestration boundary that may register the skill later.
- AgentsSdkStyleReportRuntime: current SDK adapter with an explicit dry-run
  switch and future `Runner.run` path.

The scaffold connector reports configured=false and performs no network
request. Canva credentials, OAuth flow, MCP endpoint, asset copying, and
export operations are intentionally deferred.

## Future safety rule

The agent may consume persisted questionnaire evidence. It must not make the
Google importer depend on Canva or OpenAI availability.
