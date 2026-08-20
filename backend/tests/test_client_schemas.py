from app.api.schemas.clients import UpdateClientRequest


def test_update_client_request_trims_display_name() -> None:
    request = UpdateClientRequest(display_name="  Synthetic Client  ")

    assert request.display_name == "Synthetic Client"


def test_update_client_request_allows_clearing_display_name() -> None:
    request = UpdateClientRequest(display_name="   ")

    assert request.display_name is None
