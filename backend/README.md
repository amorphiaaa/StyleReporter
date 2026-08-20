# Backend scaffold and import prototype

The backend exposes health, a manual import endpoint, and an import-run lookup.
The endpoint accepts already-read rows and persists them through SQLAlchemy
repositories; the real Google Sheets provider is not connected yet.

## Commands

    uv sync --dev
    uv run uvicorn app.main:app --reload
    uv run pytest
    uv run ruff check .

## Implementation boundaries

- Google Sheets adapter: app/integrations/google_sheets.py
- Questionnaire orchestration: app/services/questionnaire_importer.py
- Repositories: app/repositories/
- Agents SDK runtime: app/agents/runtime.py
- Canva connector: app/agents/canva.py
