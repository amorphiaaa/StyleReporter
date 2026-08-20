from sqlalchemy.dialects.postgresql import JSONB

import app.db.models  # noqa: F401
from app.db.base import Base


def test_persistence_foundation_registers_expected_tables() -> None:
    assert set(Base.metadata.tables) == {
        "clients",
        "questionnaire_submissions",
        "import_runs",
        "style_report_runs",
    }


def test_client_email_is_unique() -> None:
    table = Base.metadata.tables["clients"]
    email_constraint = next(
        constraint
        for constraint in table.constraints
        if constraint.name == "uq_clients_email_normalized"
    )

    assert {column.name for column in email_constraint.columns} == {"email_normalized"}


def test_submission_keeps_raw_payload_as_jsonb_and_source_row_is_unique() -> None:
    table = Base.metadata.tables["questionnaire_submissions"]
    source_constraint = next(
        constraint
        for constraint in table.constraints
        if constraint.name == "uq_questionnaire_submission_source_row"
    )

    assert isinstance(table.c.raw_payload.type, JSONB)
    assert {column.name for column in source_constraint.columns} == {
        "source_spreadsheet_id",
        "source_sheet_name",
        "source_row_number",
    }


def test_import_run_keeps_duplicate_counter() -> None:
    table = Base.metadata.tables["import_runs"]

    assert table.c.skipped_duplicates.nullable is False


def test_style_report_run_keeps_report_json_and_relationship_keys() -> None:
    table = Base.metadata.tables["style_report_runs"]

    assert isinstance(table.c.report.type, JSONB)
    assert table.c.client_id.foreign_keys
    assert table.c.submission_id.foreign_keys
