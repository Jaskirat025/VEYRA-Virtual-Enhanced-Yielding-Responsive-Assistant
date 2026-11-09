from __future__ import annotations

import json

import pytest
from backend.integrations import google_oauth

CLIENT_ID = "000000000000-example.apps.googleusercontent.com"
CLIENT_SECRET = "example-client-secret"


def test_builtin_client_can_come_from_environment(monkeypatch, tmp_path):
    monkeypatch.setattr(google_oauth, "CLIENT_FILE", tmp_path / "missing.json")
    monkeypatch.setenv(google_oauth.CLIENT_ID_ENV, CLIENT_ID)
    monkeypatch.setenv(google_oauth.CLIENT_SECRET_ENV, CLIENT_SECRET)

    config = google_oauth.builtin_client_config()

    assert config is not None
    assert config["installed"]["client_id"] == CLIENT_ID
    assert config["installed"]["client_secret"] == CLIENT_SECRET


def test_builtin_client_can_come_from_the_packaged_file(monkeypatch, tmp_path):
    client_file = tmp_path / "google_client.json"
    client_file.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(google_oauth, "CLIENT_FILE", client_file)
    monkeypatch.delenv(google_oauth.CLIENT_ID_ENV, raising=False)
    monkeypatch.delenv(google_oauth.CLIENT_SECRET_ENV, raising=False)

    config = google_oauth.builtin_client_config()

    assert config is not None
    assert config["installed"]["client_id"] == CLIENT_ID


def test_partial_environment_is_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(google_oauth, "CLIENT_FILE", tmp_path / "missing.json")
    monkeypatch.setenv(google_oauth.CLIENT_ID_ENV, CLIENT_ID)
    monkeypatch.delenv(google_oauth.CLIENT_SECRET_ENV, raising=False)

    with pytest.raises(google_oauth.GoogleAuthError, match="both"):
        google_oauth.builtin_client_config()


def test_missing_client_is_reported_before_importing_google_libraries(monkeypatch, tmp_path):
    monkeypatch.setattr(google_oauth, "CLIENT_FILE", tmp_path / "missing.json")
    monkeypatch.delenv(google_oauth.CLIENT_ID_ENV, raising=False)
    monkeypatch.delenv(google_oauth.CLIENT_SECRET_ENV, raising=False)
    monkeypatch.setattr(google_oauth, "get_secret", lambda name: None)

    with pytest.raises(google_oauth.GoogleAuthError, match="not configured"):
        google_oauth.connect()


def test_client_configured_reflects_environment(monkeypatch, tmp_path):
    monkeypatch.setattr(google_oauth, "CLIENT_FILE", tmp_path / "missing.json")
    monkeypatch.delenv(google_oauth.CLIENT_ID_ENV, raising=False)
    monkeypatch.delenv(google_oauth.CLIENT_SECRET_ENV, raising=False)
    monkeypatch.setattr(google_oauth, "get_secret", lambda name: None)
    assert google_oauth.client_configured() is False

    monkeypatch.setenv(google_oauth.CLIENT_ID_ENV, CLIENT_ID)
    monkeypatch.setenv(google_oauth.CLIENT_SECRET_ENV, CLIENT_SECRET)
    assert google_oauth.client_configured() is True


def test_invalid_client_config_is_rejected():
    with pytest.raises(google_oauth.GoogleAuthError):
        google_oauth.save_client_config({"installed": {"client_id": "invalid"}})
