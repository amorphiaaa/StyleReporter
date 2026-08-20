import httpx
import pytest

from app.domain.contracts import SheetReadRequest
from app.integrations.google_sheets import (
    GoogleSheetsApiError,
    GoogleSheetsApiSource,
    GoogleSheetsConfigurationError,
    GoogleSheetsHttpTransport,
)


class FakeAccessTokenProvider:
    async def get_access_token(self) -> str:
        return "synthetic-access-token"


class FakeSheetsTransport:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.calls: list[tuple[str, str, str]] = []

    async def get_values(
        self,
        *,
        spreadsheet_id: str,
        cell_range: str,
        access_token: str,
    ) -> dict[str, object]:
        self.calls.append((spreadsheet_id, cell_range, access_token))
        return self.response


@pytest.mark.asyncio
async def test_google_sheets_source_maps_headers_and_preserves_rows() -> None:
    transport = FakeSheetsTransport(
        {
            "values": [
                ["Timestamp", "Email", "Email", ""],
                ["2026-08-20 12:00", " Client@Example.test ", "alt", "image-url"],
                ["2026-08-21 12:00", "second@example.test"],
            ]
        }
    )
    source = GoogleSheetsApiSource(
        access_token_provider=FakeAccessTokenProvider(),
        transport=transport,
    )

    rows = await source.read_rows(
        SheetReadRequest(
            spreadsheet_id="synthetic-spreadsheet",
            sheet_name="Form Responses 1",
            cell_range="'Form Responses 1'!A5:D",
        )
    )

    assert transport.calls == [
        ("synthetic-spreadsheet", "'Form Responses 1'!A5:D", "synthetic-access-token")
    ]
    assert [row.row_number for row in rows] == [6, 7]
    assert rows[0].values == {
        "Timestamp": "2026-08-20 12:00",
        "Email": " Client@Example.test ",
        "Email__2": "alt",
        "column_4": "image-url",
    }
    assert rows[1].values["Email"] == "second@example.test"
    assert rows[1].values["column_4"] == ""


@pytest.mark.asyncio
async def test_google_sheets_source_returns_empty_for_empty_sheet() -> None:
    source = GoogleSheetsApiSource(
        access_token_provider=FakeAccessTokenProvider(),
        transport=FakeSheetsTransport({}),
    )

    rows = await source.read_rows(
        SheetReadRequest(spreadsheet_id="synthetic-spreadsheet", sheet_name="Responses")
    )

    assert rows == []


def test_google_sheets_source_rejects_missing_service_account_config() -> None:
    with pytest.raises(GoogleSheetsConfigurationError, match="GOOGLE_SERVICE_ACCOUNT_JSON"):
        GoogleSheetsApiSource.from_service_account_json("")


@pytest.mark.asyncio
async def test_google_sheets_http_transport_maps_upstream_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer synthetic-access-token"
        assert request.url.params["majorDimension"] == "ROWS"
        return httpx.Response(
            status_code=403,
            json={"error": {"message": "permission denied"}},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        transport = GoogleSheetsHttpTransport(client=client)

        with pytest.raises(GoogleSheetsApiError) as exc_info:
            await transport.get_values(
                spreadsheet_id="synthetic-spreadsheet",
                cell_range="'Responses'",
                access_token="synthetic-access-token",
            )
    finally:
        await client.aclose()

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "permission denied"
