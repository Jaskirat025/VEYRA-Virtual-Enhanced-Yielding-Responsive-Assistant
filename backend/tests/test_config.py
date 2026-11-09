from __future__ import annotations

import json

from backend.config import AppSettings, SettingsStore


def test_defaults_are_stable():
    settings = AppSettings()
    assert settings.assistant_name == "Veyra"
    assert settings.wake_word == "hey veyra"
    assert settings.models.local_model == "qwen3:4b"
    assert settings.models.context_tokens == 4096
    assert settings.interface.language == "en"
    assert settings.tool_enabled("calcola") is True


def test_save_and_load_roundtrip(tmp_path):
    store = SettingsStore(tmp_path / "config.json")
    settings = store.load()
    settings.assistant_name = "Nova"
    settings.interface.language = "it"
    store.save(settings)

    reloaded = SettingsStore(tmp_path / "config.json").load()
    assert reloaded.assistant_name == "Nova"
    assert reloaded.interface.language == "it"


def test_corrupt_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not json", encoding="utf-8")
    settings = SettingsStore(path).load()
    assert settings.assistant_name == "Veyra"


def test_unknown_language_is_reset_to_english(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"interface": {"language": "xx"}}), encoding="utf-8")
    assert SettingsStore(path).load().interface.language == "en"


def test_environment_override(tmp_path, monkeypatch):
    monkeypatch.setenv("VEYRA_LOCAL_MODEL", "qwen3:8b")
    monkeypatch.setenv("VEYRA_LOW_POWER", "true")
    settings = SettingsStore(tmp_path / "config.json").load()
    assert settings.models.local_model == "qwen3:8b"
    assert settings.interface.low_power is True


def test_partial_update_merges(tmp_path):
    store = SettingsStore(tmp_path / "config.json")
    updated = store.update({"voice": {"engine": "pyttsx3"}, "assistant_name": "Aria"})
    assert updated.voice.engine == "pyttsx3"
    assert updated.assistant_name == "Aria"
    assert updated.models.local_model == "qwen3:4b"


def test_tool_permissions_default_to_enabled():
    settings = AppSettings(tool_permissions={"elimina_file": False})
    assert settings.tool_enabled("elimina_file") is False
    assert settings.tool_enabled("salva_nota") is True
