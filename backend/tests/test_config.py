from app.core.config import Settings


def test_real_agents_sdk_runtime_is_disabled_by_default() -> None:
    settings = Settings(_env_file=None)

    assert settings.openai_agent_runtime_enabled is False
    assert settings.codex_cli_enabled is False
