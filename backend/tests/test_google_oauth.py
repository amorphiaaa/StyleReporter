import json
from datetime import datetime, timedelta

import pytest

from app.integrations.google_oauth import OAuthAccessTokenProvider


@pytest.mark.asyncio
async def test_oauth_provider_refreshes_user_credentials_without_network() -> None:
    provider = OAuthAccessTokenProvider(
        json.dumps(
            {
                "installed": {
                    "client_id": "synthetic-client-id",
                    "client_secret": "synthetic-client-secret",
                    "token_uri": "https://oauth.example.test/token",
                }
            }
        ),
        "synthetic-refresh-token",
    )

    def fake_refresh(_request: object) -> None:
        provider._credentials.token = "synthetic-access-token"
        provider._credentials.expiry = datetime.now() + timedelta(minutes=5)

    provider._credentials.refresh = fake_refresh

    assert await provider.get_access_token() == "synthetic-access-token"
    assert await provider.get_access_token() == "synthetic-access-token"
