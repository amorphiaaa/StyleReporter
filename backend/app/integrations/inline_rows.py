from collections.abc import Sequence

from app.domain.contracts import GoogleSheetsSource, SheetReadRequest, SheetRow


class InlineRowsSource(GoogleSheetsSource):
    """Source boundary for rows supplied by an internal API caller."""

    def __init__(self, rows: Sequence[SheetRow]) -> None:
        self._rows = tuple(rows)

    async def read_rows(self, request: SheetReadRequest) -> Sequence[SheetRow]:
        return self._rows
