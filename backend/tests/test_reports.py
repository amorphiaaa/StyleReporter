import pytest
from fastapi import HTTPException

from app.api.routes.reports import _build_runtime
from app.core.config import Settings


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
