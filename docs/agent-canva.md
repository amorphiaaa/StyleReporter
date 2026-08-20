# Agents SDK and Canva boundary

The backend includes a future agent runtime boundary, but it does not create an
agent, call a model, load prompts, or execute tools.

The planned runtime will use the Python Agents SDK:

- Official OpenAI Agents documentation:
  https://developers.openai.com/api/docs/guides/agents
- Python SDK documentation:
  https://openai.github.io/openai-agents-python/

The openai-agents dependency is present so the future implementation can be
added without reshaping the repository. It is not imported by the scaffold
runtime.

## Separate concepts

- CanvaSkill: domain capability description and future tool surface.
- CanvaConnector: transport/auth boundary for a future Canva OAuth or MCP
  integration.
- AgentRuntime: orchestration boundary that may register the skill later.

The scaffold connector reports configured=false and performs no network
request. Canva credentials, OAuth flow, MCP endpoint, asset copying, and
export operations are intentionally deferred.

## Future safety rule

The agent may consume persisted questionnaire evidence. It must not make the
Google importer depend on Canva or OpenAI availability.
