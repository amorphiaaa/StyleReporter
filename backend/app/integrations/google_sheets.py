from collections.abc import Sequence

from app.domain.contracts import GoogleSheetsSource, SheetReadRequest, SheetRow


class ScaffoldGoogleSheetsSource(GoogleSheetsSource):
    """Contract placeholder for a future read-only Google Sheets adapter."""

    async def read_rows(self, request: SheetReadRequest) -> Sequence[SheetRow]:
        raise NotImplementedError(
            "Google Sheets integration is intentionally not implemented in the scaffold."
        )
