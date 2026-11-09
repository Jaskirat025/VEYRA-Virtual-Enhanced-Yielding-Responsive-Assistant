from __future__ import annotations

from backend.api.app import create_app
from backend.config import SettingsStore
from fastapi.testclient import TestClient

TOKEN = "test-session-token"


def make_client(tmp_path):
    store = SettingsStore(tmp_path / "config.json")
    from backend.memory.db import Database

    db = Database(tmp_path / "api.db")
    app = create_app(store, db, TOKEN)
    return TestClient(app)


def headers():
    return {"X-Veyra-Token": TOKEN}


def test_requests_without_token_are_rejected(tmp_path):
    with make_client(tmp_path) as client:
        assert client.get("/api/health").status_code == 401
        assert client.get("/api/health", headers={"X-Veyra-Token": "wrong"}).status_code == 401


def test_health_with_token(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/api/health", headers=headers())
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_settings_roundtrip(tmp_path):
    with make_client(tmp_path) as client:
        response = client.put(
            "/api/settings",
            headers=headers(),
            json={"patch": {"assistant_name": "Nova", "interface": {"language": "it"}}},
        )
        assert response.status_code == 200
        assert (
            client.get("/api/settings", headers=headers()).json()["settings"]["assistant_name"]
            == "Nova"
        )


def test_tools_endpoint_lists_risks(tmp_path):
    with make_client(tmp_path) as client:
        tools = client.get("/api/tools", headers=headers()).json()["tools"]
    names = {tool["name"]: tool for tool in tools}
    assert names["elimina_file"]["risk"] == "dangerous"
    assert names["calcola"]["risk"] == "safe"
    assert names["calcola"]["enabled"] is True


def test_secrets_are_never_returned(tmp_path):
    with make_client(tmp_path) as client:
        saved = client.post(
            "/api/secrets",
            headers=headers(),
            json={"name": "github_token", "value": "example-value"},
        )
        assert saved.status_code == 200
        assert saved.json()["status"]["github_token"] is True
        assert "example-value" not in saved.text

        removed = client.delete("/api/secrets/github_token", headers=headers())
        assert removed.json()["status"]["github_token"] is False


def test_bootstrap_status_lists_both_downloads(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/api/bootstrap/status", headers=headers())
    assert response.status_code == 200
    data = response.json()
    assert data["running"] is False
    assert {job["id"] for job in data["jobs"]} == {"local_model", "speech_model"}


def test_gmail_app_password_secret_is_accepted(tmp_path):
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/secrets",
            headers=headers(),
            json={"name": "gmail_app_password", "value": "example-app-password"},
        )
    assert response.status_code == 200
    assert response.json()["saved"] is True
    assert "example-app-password" not in response.text


def test_custom_api_secret_is_accepted(tmp_path):
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/secrets",
            headers=headers(),
            json={"name": "custom_api_exa", "value": "custom-example"},
        )
    assert response.status_code == 200
    assert response.json()["saved"] is True
    assert "custom-example" not in response.text


def test_unknown_secret_name_is_rejected(tmp_path):
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/secrets", headers=headers(), json={"name": "admin", "value": "x"}
        )
    assert response.status_code == 400
