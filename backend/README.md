# Backend scaffold

The backend is a FastAPI shell. It exposes health and contract-only placeholder
routes. Provider integrations and persistence are intentionally not implemented.

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
