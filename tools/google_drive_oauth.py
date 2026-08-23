"""Authorize a Google Drive OAuth desktop client and print its refresh token.

Run this script once on the developer workstation. It opens a browser for
Google consent, receives the loopback callback, and prints one env assignment.
The client JSON and refresh token are never written to the repository.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
DEFAULT_REDIRECT_PORT = 8765


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        values = urllib.parse.parse_qs(parsed.query)
        self.server.oauth_result = {key: items[0] for key, items in values.items()}
        body = (
            b"<html><body><h1>StyleReporter authorization received.</h1>"
            b"<p>You can close this tab and return to the terminal.</p></body></html>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> int:
    args = _parse_args()
    client = _load_client_config(Path(args.client_json))
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    redirect_uri = f"http://127.0.0.1:{args.port}/"
    auth_url = client["auth_uri"] + "?" + urllib.parse.urlencode(
        {
            "client_id": client["client_id"],
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": DRIVE_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )

    server = HTTPServer(("127.0.0.1", args.port), _OAuthCallbackHandler)
    server.timeout = args.timeout
    print("Opening Google authorization in your browser...")
    print(auth_url)
    webbrowser.open(auth_url)
    server.handle_request()
    result = getattr(server, "oauth_result", {})
    if result.get("state") != state:
        raise SystemExit("OAuth state validation failed or the callback timed out.")
    if result.get("error"):
        raise SystemExit(f"Google OAuth authorization failed: {result['error']}")
    if not result.get("code"):
        raise SystemExit("Google OAuth callback did not contain an authorization code.")

    token_payload = _exchange_code(client, result["code"], redirect_uri, verifier)
    refresh_token = token_payload.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        raise SystemExit(
            "Google returned no refresh token. Re-run the script; consent must include "
            "access_type=offline and prompt=consent."
        )
    print("\nAdd this line to .env (keep it secret):")
    print(f"GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN={refresh_token}")
    print("GOOGLE_DRIVE_OAUTH_CLIENT_JSON=" + _compact_client_json(Path(args.client_json)))
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--client-json",
        required=True,
        help="Path to the downloaded Google OAuth Desktop client JSON.",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_REDIRECT_PORT)
    parser.add_argument("--timeout", type=int, default=300)
    return parser.parse_args()


def _load_client_config(path: Path) -> dict[str, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read OAuth client JSON: {path}") from exc
    config = payload.get("installed") or payload.get("web")
    if not isinstance(config, dict):
        raise SystemExit("OAuth client JSON must contain an 'installed' or 'web' object.")
    required = ("client_id", "auth_uri", "token_uri")
    if any(not isinstance(config.get(key), str) for key in required):
        raise SystemExit("OAuth client JSON is missing client_id, auth_uri, or token_uri.")
    return {
        "client_id": config["client_id"],
        "client_secret": str(config.get("client_secret", "")),
        "auth_uri": config["auth_uri"],
        "token_uri": config["token_uri"],
    }


def _compact_client_json(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read OAuth client JSON: {path}") from exc
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _exchange_code(
    client: dict[str, str],
    code: str,
    redirect_uri: str,
    verifier: str,
) -> dict[str, Any]:
    payload = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": client["client_id"],
            "client_secret": client["client_secret"],
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        }
    ).encode("ascii")
    request = urllib.request.Request(
        client["token_uri"],
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as exc:
        raise SystemExit("Google OAuth token exchange failed.") from exc
    if not isinstance(result, dict):
        raise SystemExit("Google OAuth token response was invalid.")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
