from app.core.config import Settings


def test_removed_provider_settings_are_not_configured() -> None:
    settings = Settings(_env_file=None)

    assert not hasattr(settings, "openai_api_key")
    assert not hasattr(settings, "codex_cli_enabled")
