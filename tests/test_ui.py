from fastapi.testclient import TestClient

from app.main import app


def test_ui_root_serves_dashboard() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "PR Review Agent" in response.text


def test_api_info_serves_service_metadata() -> None:
    client = TestClient(app)

    response = client.get("/api/info")

    assert response.status_code == 200
    assert response.json()["webhook"] == "/api/github/webhook"
