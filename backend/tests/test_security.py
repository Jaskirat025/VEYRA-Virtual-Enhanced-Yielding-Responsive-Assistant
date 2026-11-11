from __future__ import annotations

from pathlib import Path

import pytest
from backend.api.app import create_app
from backend.config import SettingsStore
from backend.memory.db import Database
from backend.tools.builtin.files import _user_path
from backend.tools.registry import ToolError
from fastapi.testclient import TestClient

TOKEN = "test-session-token"
HEADERS = {"X-Veyra-Token": TOKEN}


def test_user_path_rejects_sibling_with_shared_prefix():
    home = Path.home().resolve()
    sibling = Path(str(home) + "2") / "outside.txt"
    with pytest.raises(ToolError, match="outside the user folder"):
        _user_path(str(sibling), must_exist=False)


def test_delete_my_data_clears_database_settings_and_key_value_store(tmp_path):
    store = SettingsStore(tmp_path / "config.json")
    db = Database(tmp_path / "privacy.db")
    store.update({"assistant_name": "Private user"})
    db.set_value("onboarded", "1")
    db.set_value("last_conversation_id", "conversation-1")
    db.add_message("conversation-1", "user", "a private message")

    with TestClient(create_app(store, db, TOKEN)) as client:
        response = client.delete("/api/privacy/data", headers=HEADERS)

    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert response.json()["restart_required"] is True
    assert db.get_value("onboarded") == ""
    assert db.get_value("last_conversation_id") == ""
    assert db.messages("conversation-1") == []
    assert store.load().assistant_name == "Veyra"
    db.close()
