import base64
import hashlib
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.config import get_settings
from app.integrations.canva_connect import CanvaConnectError, CanvaConnectProvider

router = APIRouter(prefix="/canva/oauth", tags=["canva-auth"])


@router.get("/start", response_class=RedirectResponse, include_in_schema=False)
async def start_canva_oauth(request: Request) -> RedirectResponse:
    settings = get_settings()
    if not settings.canva_enabled or not settings.canva_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Canva OAuth is not configured.",
        )

    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    state = secrets.token_urlsafe(32)
    request.app.state.canva_oauth_pending[state] = verifier
    query = urlencode(
        {
            "code_challenge": challenge,
            "code_challenge_method": "s256",
            "scope": settings.canva_scopes,
            "response_type": "code",
            "client_id": settings.canva_client_id,
            "state": state,
            "redirect_uri": settings.canva_redirect_uri,
        }
    )
    return RedirectResponse(f"https://www.canva.com/api/oauth/authorize?{query}")


@router.get("/callback", response_class=HTMLResponse, include_in_schema=False)
async def finish_canva_oauth(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> HTMLResponse:
    if error:
        return HTMLResponse(
            f"<h1>Canva connection was cancelled</h1><p>{error}</p>", status_code=400
        )
    settings = get_settings()
    verifier = request.app.state.canva_oauth_pending.pop(state or "", None)
    provider = getattr(request.app.state, "canva_provider", None)
    if not code or not verifier or not isinstance(provider, CanvaConnectProvider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Canva OAuth callback.",
        )
    if not settings.canva_client_id or not settings.canva_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Canva OAuth client credentials are not configured.",
        )
    try:
        token = await provider.exchange_authorization_code(
            code=code,
            code_verifier=verifier,
            redirect_uri=settings.canva_redirect_uri,
            client_id=settings.canva_client_id,
            client_secret=settings.canva_client_secret,
        )
    except CanvaConnectError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    request.app.state.canva_refresh_token = token.get("refresh_token")
    return HTMLResponse(
        "<h1>Canva connected</h1><p>You can close this window and return to StyleReporter.</p>"
    )
