from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

import httpx
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

from app.domain.contracts import GoogleSheetsSource, SheetReadRequest, SheetRow

GOOGLE_SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
GOOGLE_SHEETS_VALUES_URL = "https://sheets.googleapis.com/v4/spreadsheets"


class GoogleSheetsConfigurationError(RuntimeError):
    """Raised when the provider cannot be configured without making an API call."""


class GoogleSheetsAuthenticationError(RuntimeError):
    """Raised when a service-account access token cannot be obtained."""


class GoogleSheetsApiError(RuntimeError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class GoogleAccessTokenProvider(Protocol):
    async def get_access_token(self) -> str:
        ...


class GoogleSheetsTransport(Protocol):
    async def get_values(
        self,
        *,
        spreadsheet_id: str,
        cell_range: str,
        access_token: str,
    ) -> Mapping[str, Any]:
        ...


class ServiceAccountAccessTokenProvider:
    """Refreshes a read-only service-account token on demand."""

    def __init__(self, service_account_json: str) -> None:
        try:
            self._credentials = _load_service_account_credentials(service_account_json)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise GoogleSheetsConfigurationError(
                "GOOGLE_SERVICE_ACCOUNT_JSON must contain service-account JSON "
                "or a valid file path."
            ) from exc
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
                    "Google service-account authentication failed."
                ) from exc

        if not self._credentials.token:
            raise GoogleSheetsAuthenticationError(
                "Google service-account authentication returned no access token."
            )
        return self._credentials.token


class GoogleSheetsHttpTransport:
    """Read-only HTTP transport for spreadsheets.values.get."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
        base_url: str = GOOGLE_SHEETS_VALUES_URL,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._client = client
        self._base_url = base_url.rstrip("/")

    async def get_values(
        self,
        *,
        spreadsheet_id: str,
        cell_range: str,
        access_token: str,
    ) -> Mapping[str, Any]:
        url = (
            f"{self._base_url}/{quote(spreadsheet_id, safe='')}/values/"
            f"{quote(cell_range, safe='')}"
        )
        params = {
            "majorDimension": "ROWS",
            "valueRenderOption": "FORMATTED_VALUE",
        }
        headers = {"Authorization": f"Bearer {access_token}"}

        if self._client is not None:
            response = await self._client.get(url, params=params, headers=headers)
            return _parse_google_response(response)

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.get(url, params=params, headers=headers)
        return _parse_google_response(response)


class GoogleSheetsApiSource(GoogleSheetsSource):
    """Read a Google Sheet's first row as headers and remaining rows as payloads."""

    def __init__(
        self,
        *,
        access_token_provider: GoogleAccessTokenProvider,
        transport: GoogleSheetsTransport | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._access_token_provider = access_token_provider
        self._transport = transport or GoogleSheetsHttpTransport(
            timeout_seconds=timeout_seconds
        )

    @classmethod
    def from_service_account_json(
        cls,
        service_account_json: str,
        *,
        timeout_seconds: float = 10.0,
    ) -> GoogleSheetsApiSource:
        return cls(
            access_token_provider=ServiceAccountAccessTokenProvider(service_account_json),
            timeout_seconds=timeout_seconds,
        )

    async def read_rows(self, request: SheetReadRequest) -> Sequence[SheetRow]:
        access_token = await self._access_token_provider.get_access_token()
        response = await self._transport.get_values(
            spreadsheet_id=request.spreadsheet_id,
            cell_range=_effective_cell_range(request),
            access_token=access_token,
        )
        values = response.get("values", [])
        if not isinstance(values, list):
            raise GoogleSheetsApiError(502, "Google Sheets response contains invalid values.")
        if not values:
            return []
        if not all(isinstance(row, list) for row in values):
            raise GoogleSheetsApiError(502, "Google Sheets response rows are invalid.")

        rows = [[_cell_to_text(cell) for cell in row] for row in values]
        headers = _build_headers(rows)
        first_row_number = _starting_row_number(request.cell_range)
        return [
            SheetRow(
                row_number=first_row_number + index,
                values={
                    header: row[column_index] if column_index < len(row) else ""
                    for column_index, header in enumerate(headers)
                },
            )
            for index, row in enumerate(rows[1:], start=1)
        ]


class ScaffoldGoogleSheetsSource(GoogleSheetsSource):
    """Contract placeholder retained for documentation and explicit scaffolding."""

    async def read_rows(self, request: SheetReadRequest) -> Sequence[SheetRow]:
        raise NotImplementedError(
            "Google Sheets integration is intentionally not implemented in the scaffold."
        )


class FixtureGoogleSheetsSource(GoogleSheetsSource):
    """Deterministic local source used to exercise the import boundary."""

    def __init__(
        self,
        rows: Sequence[SheetRow],
        *,
        spreadsheet_id: str = "synthetic-spreadsheet",
        sheet_name: str = "Form Responses 1",
    ) -> None:
        self._rows = tuple(rows)
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name

    async def read_rows(self, request: SheetReadRequest) -> Sequence[SheetRow]:
        if request.spreadsheet_id != self._spreadsheet_id:
            raise ValueError("Fixture spreadsheet ID does not match the read request")
        if request.sheet_name != self._sheet_name:
            raise ValueError("Fixture sheet name does not match the read request")
        return self._rows


def _load_service_account_credentials(
    service_account_json: str,
) -> service_account.Credentials:
    value = service_account_json.strip()
    if not value:
        raise ValueError("service-account credentials are empty")
    if value.startswith("{"):
        info = json.loads(value)
        return service_account.Credentials.from_service_account_info(
            info,
            scopes=[GOOGLE_SHEETS_READONLY_SCOPE],
        )
    return service_account.Credentials.from_service_account_file(
        str(Path(value)),
        scopes=[GOOGLE_SHEETS_READONLY_SCOPE],
    )


def _parse_google_response(response: httpx.Response) -> Mapping[str, Any]:
    if response.is_error:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        detail = payload.get("error", {}).get("message") if isinstance(payload, dict) else None
        raise GoogleSheetsApiError(
            response.status_code,
            detail or "Google Sheets API request failed.",
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise GoogleSheetsApiError(502, "Google Sheets API returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise GoogleSheetsApiError(502, "Google Sheets API returned an invalid payload.")
    return payload


def _effective_cell_range(request: SheetReadRequest) -> str:
    if request.cell_range:
        return request.cell_range
    return f"'{request.sheet_name}'"


def _starting_row_number(cell_range: str | None) -> int:
    if not cell_range:
        return 1
    match = re.search(r"(?:^|!)[A-Za-z]+(\d+)", cell_range)
    return int(match.group(1)) if match else 1


def _build_headers(rows: Sequence[Sequence[str]]) -> list[str]:
    column_count = max(len(row) for row in rows)
    headers: list[str] = []
    seen: dict[str, int] = {}
    for index in range(column_count):
        raw_header = rows[0][index] if index < len(rows[0]) else ""
        base_header = raw_header.strip() or f"column_{index + 1}"
        seen[base_header] = seen.get(base_header, 0) + 1
        header = (
            base_header if seen[base_header] == 1 else f"{base_header}__{seen[base_header]}"
        )
        headers.append(header)
    return headers


def _cell_to_text(value: Any) -> str:
    return "" if value is None else str(value)
