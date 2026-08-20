from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_describes_scaffold_stage() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "style-reporter-api",
        "stage": "scaffold",
    }


def test_future_workflow_routes_are_explicitly_unimplemented() -> None:
    response = TestClient(app).post("/api/v1/imports/google-sheets/sync")

    assert response.status_code == 501
