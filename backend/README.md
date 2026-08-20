# Backend scaffold and import prototype

The backend exposes health and contract-only placeholder routes. A local
synthetic source and provider-agnostic questionnaire importer are available
for testing; they are not wired to FastAPI or PostgreSQL yet.

## Commands

    uv sync --dev
    uv run uvicorn app.main:app --reload
    uv run pytest
    uv run ruff check .

## Future implementation boundaries

- Google Sheets adapter: app/integrations/google_sheets.py
- Questionnaire orchestration: app/services/questionnaire_importer.py
- Repositories: app/repositories/
- Agents SDK runtime: app/agents/runtime.py
- Canva connector: app/agents/canva.py
