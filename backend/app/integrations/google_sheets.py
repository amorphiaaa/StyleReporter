from collections.abc import Sequence

from app.domain.contracts import GoogleSheetsSource, SheetReadRequest, SheetRow


class ScaffoldGoogleSheetsSource(GoogleSheetsSource):
    """Contract placeholder for a future read-only Google Sheets adapter."""

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
