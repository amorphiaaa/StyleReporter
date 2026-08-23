"""OAuth refresh-token access for user-owned Google Workspace resources."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials

from app.integrations.google_sheets import (
    GoogleAccessTokenProvider,
    GoogleSheetsAuthenticationError,
)

GOOGLE_DRIVE_OAUTH_SCOPE = "https://www.googleapis.com/auth/drive"


class OAuthAccessTokenProvider(GoogleAccessTokenProvider):
    """Refresh a user OAuth token without storing client secrets in the repo."""

    def __init__(
        self,
        client_json: str,
        refresh_token: str,
        *,
        scopes: Sequence[str] = (GOOGLE_DRIVE_OAUTH_SCOPE,),
    ) -> None:
        client_config = _load_oauth_client_config(client_json)
        if not refresh_token.strip():
            raise GoogleSheetsAuthenticationError(
                "GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN must not be empty."
            )
        self._credentials = Credentials(
            token=None,
            refresh_token=refresh_token.strip(),
            token_uri=client_config["token_uri"],
            client_id=client_config["client_id"],
            client_secret=client_config.get("client_secret"),
            scopes=list(scopes),
        )
        self._lock = asyncio.Lock()

    async def get_access_token(self) -> str:
        if self._credentials.valid and self._credentials.token:
            return self._credentials.token

        async with self._lock:
            if self._credentials.valid and self._credentials.token:
                return self._credentials.token
            try:
                await asyncio.to_thread(self._credentials.refresh, GoogleAuthRequest())
            except Exception as exc:
                raise GoogleSheetsAuthenticationError(
                    "Google OAuth refresh failed. Re-authorize the Drive account."
                ) from exc

        if not self._credentials.token:
            raise GoogleSheetsAuthenticationError(
                "Google OAuth refresh returned no access token."
            )
        return self._credentials.token


def _load_oauth_client_config(client_json: str) -> dict[str, Any]:
    value = client_json.strip()
    if not value:
        raise GoogleSheetsAuthenticationError(
            "GOOGLE_DRIVE_OAUTH_CLIENT_JSON must contain OAuth client JSON or a file path."
        )
    try:
        payload = (
            json.loads(Path(value).read_text(encoding="utf-8"))
            if not value.startswith("{")
            else json.loads(value)
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise GoogleSheetsAuthenticationError(
            "GOOGLE_DRIVE_OAUTH_CLIENT_JSON must contain valid OAuth client JSON or a file path."
        ) from exc

    if not isinstance(payload, dict):
        raise GoogleSheetsAuthenticationError("Google OAuth client JSON must be an object.")
    config = payload.get("installed") or payload.get("web")
    if not isinstance(config, dict):
        raise GoogleSheetsAuthenticationError(
            "Google OAuth client JSON must contain an 'installed' or 'web' object."
        )
    client_id = config.get("client_id")
    token_uri = config.get("token_uri")
    if not isinstance(client_id, str) or not client_id.strip():
        raise GoogleSheetsAuthenticationError("Google OAuth client JSON has no client_id.")
    if not isinstance(token_uri, str) or not token_uri.strip():
        raise GoogleSheetsAuthenticationError("Google OAuth client JSON has no token_uri.")
    return {
        "client_id": client_id.strip(),
        "client_secret": config.get("client_secret"),
        "token_uri": token_uri.strip(),
    }
