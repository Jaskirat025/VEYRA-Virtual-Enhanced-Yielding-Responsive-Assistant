"""Application settings: model, audio, integrations and interface preferences.

Settings are stored as JSON in the per-user data directory. Secrets are never
stored here; they live in Windows Credential Manager (see ``backend.secrets``).
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from backend.paths import config_path

SUPPORTED_LANGUAGES = ("en", "it", "zh")


class ModelSettings(BaseModel):
    local_model: str = "qwen3:4b"
    context_tokens: int = Field(default=4096, ge=512, le=8192)
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    online_enabled: bool = False
    online_base_url: str = ""
    online_model: str = ""
    online_api_style: str = "openai"

    @field_validator("online_base_url")
    @classmethod
    def _strip_base_url(cls, value: str) -> str:
        return value.strip().rstrip("/")


class VoiceSettings(BaseModel):
    engine: str = "piper"
    piper_voice: str = ""
    rate: int = Field(default=180, ge=80, le=320)
    volume: float = Field(default=1.0, ge=0.0, le=1.0)
    speak_replies: bool = True


class AudioSettings(BaseModel):
    input_device: int | None = None
    stt_model: str = "base"
    stt_compute_type: str = "int8"
    vad_threshold: float = Field(default=0.02, ge=0.001, le=0.5)
    silence_ms: int = Field(default=900, ge=200, le=5000)
    max_utterance_s: float = Field(default=20.0, ge=3.0, le=120.0)
    wake_engine: str = "openwakeword"
    wake_model_path: str = ""
    push_to_talk: bool = True


class IntegrationSettings(BaseModel):
    github_login: str = ""
    github_read_only: bool = True
    google_read_only: bool = True


class InterfaceSettings(BaseModel):
    language: str = "en"
    low_power: bool = False
    mini_widget: bool = False
    autostart: bool = False
    close_to_tray: bool = True

    @field_validator("language")
    @classmethod
    def _check_language(cls, value: str) -> str:
        return value if value in SUPPORTED_LANGUAGES else "en"


class AppSettings(BaseModel):
    assistant_name: str = Field(default="Veyra", min_length=1, max_length=32)
    wake_word: str = Field(default="hey veyra", min_length=2, max_length=64)
    system_prompt: str = ""
    models: ModelSettings = Field(default_factory=ModelSettings)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    integrations: IntegrationSettings = Field(default_factory=IntegrationSettings)
    interface: InterfaceSettings = Field(default_factory=InterfaceSettings)
    tool_permissions: dict[str, bool] = Field(default_factory=dict)
    ram_floor_mb: int = Field(default=900, ge=256, le=4096)

    def tool_enabled(self, name: str) -> bool:
        """Tools are enabled unless the user explicitly disabled them."""
        return self.tool_permissions.get(name, True)


def _env_override(settings: AppSettings) -> AppSettings:
    """Apply optional environment overrides used by developers and CI."""
    data = settings.model_dump()

    def env(name: str) -> str | None:
        value = os.environ.get(name)
        return value if value else None

    if value := env("VEYRA_LOCAL_MODEL"):
        data["models"]["local_model"] = value
    if value := env("VEYRA_CONTEXT_TOKENS"):
        with contextlib.suppress(ValueError):
            data["models"]["context_tokens"] = int(value)
    if value := env("VEYRA_TEMPERATURE"):
        with contextlib.suppress(ValueError):
            data["models"]["temperature"] = float(value)
    if value := env("VEYRA_ONLINE_BASE_URL"):
        data["models"]["online_base_url"] = value
    if value := env("VEYRA_ONLINE_MODEL"):
        data["models"]["online_model"] = value
    if value := env("VEYRA_ONLINE_ENABLED"):
        data["models"]["online_enabled"] = value.lower() in {"1", "true", "yes"}
    if value := env("VEYRA_LOW_POWER"):
        data["interface"]["low_power"] = value.lower() in {"1", "true", "yes"}
    if value := env("VEYRA_UI_LANGUAGE"):
        data["interface"]["language"] = value
    return AppSettings.model_validate(data)


class SettingsStore:
    """Loads and persists settings, falling back to defaults on bad input."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or config_path()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> AppSettings:
        if not self._path.exists():
            return _env_override(AppSettings())

        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # A corrupt settings file must not prevent the app from starting.
            return _env_override(AppSettings())

        if not isinstance(raw, dict):
            return _env_override(AppSettings())

        try:
            return _env_override(AppSettings.model_validate(raw))
        except ValueError:
            return _env_override(AppSettings())

    def save(self, settings: AppSettings) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = settings.model_dump()
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._path)

    def update(self, patch: dict[str, Any]) -> AppSettings:
        """Merge a partial settings patch and persist the result."""
        current = self.load().model_dump()
        _deep_merge(current, patch)
        settings = AppSettings.model_validate(current)
        self.save(settings)
        return settings


def _deep_merge(target: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value
