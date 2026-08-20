# Agents SDK and Canva boundary

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
image URLs are treated as metadata, and the agent must not invent client facts.

The planned runtime will use the Python Agents SDK:

- Official OpenAI Agents documentation:
  https://developers.openai.com/api/docs/guides/agents
- Python SDK documentation:
  https://openai.github.io/openai-agents-python/

The `openai-agents` dependency is present and used by
`AgentsSdkStyleReportRuntime`. The real `agents_sdk` route is disabled by
default; it requires `OPENAI_AGENT_RUNTIME_ENABLED=true` and
`OPENAI_API_KEY`. Without that configuration the API returns `503`, while
`agents_sdk_dry_run` remains safe for local contract checks.

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
