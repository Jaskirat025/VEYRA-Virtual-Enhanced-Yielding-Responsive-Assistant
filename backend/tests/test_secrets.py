from __future__ import annotations

from backend import secrets as secret_store


def test_memory_fallback_roundtrip(monkeypatch):
    monkeypatch.setattr(secret_store, "_keyring_available", False, raising=False)
    secret_store.clear_memory_store()

    secret_store.set_secret("github_token", "example-value")
    assert secret_store.get_secret("github_token") == "example-value"
    assert secret_store.secret_status(["github_token", "online_api_key"]) == {
        "github_token": True,
        "online_api_key": False,
    }

    secret_store.delete_secret("github_token")
    assert secret_store.get_secret("github_token") is None


def test_environment_fallback(monkeypatch):
    monkeypatch.setattr(secret_store, "_keyring_available", False, raising=False)
    secret_store.clear_memory_store()
    monkeypatch.setenv("VEYRA_GITHUB_TOKEN", "env-token")
    assert secret_store.get_secret("github_token") == "env-token"
