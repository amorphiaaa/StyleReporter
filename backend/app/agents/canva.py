from app.domain.contracts import CanvaConnector, ConnectorStatus


class ScaffoldCanvaConnector(CanvaConnector):
    """Placeholder for a future Canva OAuth/MCP connector."""

    async def healthcheck(self) -> ConnectorStatus:
        return ConnectorStatus(
            configured=False,
            message="Canva connector is a documented future boundary only.",
        )
