# Backend scaffold and import prototype

The backend exposes health, import, client, and style-report endpoints.
Already-read rows and report runs are persisted through SQLAlchemy repositories.
The report API can call the host-side Codex CLI worker without an OpenAI API
key; the Agents SDK path is retained only as a no-network contract preview.

## Commands

    uv sync --dev
    uv run uvicorn app.main:app --reload
    uv run pytest
    uv run ruff check .

## Implementation boundaries

- Google Sheets adapter and auth/transport boundary: app/integrations/google_sheets.py
- Questionnaire orchestration: app/services/questionnaire_importer.py
- Versioned questionnaire mappings: app/domain/questionnaire_definitions/
- Repositories: app/repositories/
- Report runtime contract: app/domain/contracts.py
- Stub methodologist runtime: app/agents/style_methodologist.py
- Agents SDK dry-run and Codex CLI adapter: app/agents/runtime.py
- Canva connector: app/agents/canva.py
