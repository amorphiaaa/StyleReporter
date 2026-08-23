import pytest
from fastapi import HTTPException

from app.api.routes.reports import _build_runtime, _failed_report_run, _to_response
from app.core.config import Settings
from app.domain.contracts import StyleReportRun


def test_real_agents_sdk_runtime_returns_service_unavailable_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.api.routes.reports.get_settings",
        lambda: Settings(_env_file=None),
    )

    with pytest.raises(HTTPException) as exc_info:
        _build_runtime("agents_sdk")

    assert exc_info.value.status_code == 503
    assert "OPENAI_AGENT_RUNTIME_ENABLED=true" in str(exc_info.value.detail)


def test_codex_cli_runtime_requires_a_local_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.api.routes.reports.get_settings",
        lambda: Settings(_env_file=None, codex_cli_enabled=True),
    )

    with pytest.raises(HTTPException) as exc_info:
        _build_runtime("codex_cli")

    assert exc_info.value.status_code == 503
    assert "CODEX_CLI_RUNNER_URL" in str(exc_info.value.detail)


def test_failed_report_run_keeps_error_for_history() -> None:
    report_run = StyleReportRun(
        id="cc9f2406-74d2-4392-be2b-8377039d11d9",
        client_id="cc9f2406-74d2-4392-be2b-8377039d11d9",
        submission_id="9d0ce279-4772-4a40-932b-dcd9b3306e8c",
        status="running",
        runtime_type="agents_sdk",
        report_version="pending",
    )

    failed = _failed_report_run(report_run, RuntimeError("provider unavailable"))
    response = _to_response(failed)

    assert failed.status == "failed"
    assert failed.report_version == "failed"
    assert failed.error_message == "RuntimeError: provider unavailable"
    assert response.status == "failed"
    assert response.report is None
    assert response.error_message == "RuntimeError: provider unavailable"
