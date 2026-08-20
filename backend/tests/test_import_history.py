from datetime import UTC, datetime
from uuid import UUID

from app.api.routes.imports import _to_import_history_item
from app.db.models import ImportRun


def test_import_history_item_exposes_summary_counters() -> None:
    import_id = UUID("f71fa28b-e681-4fb9-9252-53078bd9ecf5")
    started_at = datetime(2026, 8, 20, 18, 0, tzinfo=UTC)
    import_run = ImportRun(
        id=import_id,
        source_type="google_sheets",
        source_spreadsheet_id="synthetic-spreadsheet",
        source_sheet_name="Form Responses 1",
        status="completed",
        rows_seen=4,
        created_clients=2,
        updated_clients=1,
        created_submissions=3,
        rejected_rows=1,
        skipped_duplicates=0,
        row_errors=[{"row_number": 4, "code": "invalid_email", "message": "Invalid email"}],
        started_at=started_at,
        completed_at=started_at,
    )

    item = _to_import_history_item(import_run)

    assert item.import_id == import_id
    assert item.status == "completed"
    assert item.created_submissions == 3
    assert item.row_errors_count == 1
