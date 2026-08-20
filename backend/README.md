# Backend scaffold and import prototype

The backend exposes health, manual import and client endpoints, plus a local
stub style-report endpoint. Already-read rows and report runs are persisted
through SQLAlchemy repositories; real Google Sheets and OpenAI providers are
not connected yet.

## Commands

    uv sync --dev
    uv run uvicorn app.main:app --reload
    uv run pytest
    uv run ruff check .

## Implementation boundaries

- Google Sheets adapter: app/integrations/google_sheets.py
- Questionnaire orchestration: app/services/questionnaire_importer.py
- Repositories: app/repositories/
- Report runtime contract: app/domain/contracts.py
- Stub methodologist runtime: app/agents/style_methodologist.py
- Agents SDK adapter with dry-run and gated future Runner path: app/agents/runtime.py
- Canva connector: app/agents/canva.py
