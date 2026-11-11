"""Application settings: model, audio, integrations and interface preferences.

Settings are stored as JSON in the per-user data directory. Secrets are never
stored here; they live in Windows Credential Manager (see ``backend.secrets``).
"""

from __future__ import annotations

import contextlib
import json
import os
import re
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

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


class ProactiveSettings(BaseModel):
    enabled: bool = False
    interval_minutes: int = Field(default=30, ge=5, le=240)


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


class CustomApiSettings(BaseModel):
    """A user-defined HTTP endpoint exposed to the local model as a tool."""

    id: str = Field(min_length=2, max_length=32, pattern=r"^[a-z][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=300)
    base_url: str = Field(min_length=1, max_length=500)
    path: str = Field(default="", max_length=300)
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "POST"
    auth_header: str = Field(default="Authorization", max_length=64)
    auth_prefix: str = Field(default="Bearer ", max_length=40)
    headers: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True

    @field_validator("base_url")
    @classmethod
    def _check_base_url(cls, value: str) -> str:
        cleaned = value.strip().rstrip("/")
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("The custom API base URL must be an http(s) URL.")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError(
                "The custom API base URL cannot contain credentials, a query or a fragment."
            )
        return cleaned

    @field_validator("path")
    @classmethod
    def _check_path(cls, value: str) -> str:
        cleaned = value.strip()
        if any(character.isspace() for character in cleaned):
            raise ValueError("The custom API path cannot contain spaces.")
        if any(character in cleaned for character in ("?", "#", "\\")) or ".." in cleaned:
            raise ValueError("The custom API path cannot contain queries, fragments or '..'.")
        if "://" in cleaned:
            raise ValueError("The custom API path must be relative.")
        if cleaned and not cleaned.startswith("/"):
            cleaned = "/" + cleaned
        return cleaned

    @field_validator("auth_header")
    @classmethod
    def _check_auth_header(cls, value: str) -> str:
        cleaned = value.strip()
        if not re.fullmatch(r"[A-Za-z0-9-]{1,64}", cleaned):
            raise ValueError("The authentication header name is invalid.")
        if cleaned.lower() in {
            "host",
            "content-length",
            "transfer-encoding",
            "connection",
            "cookie",
        }:
            raise ValueError("The authentication header cannot be a transport header.")
        return cleaned

    @field_validator("auth_prefix")
    @classmethod
    def _check_auth_prefix(cls, value: str) -> str:
        if "\n" in value or "\r" in value:
            raise ValueError("The authentication prefix cannot contain a newline.")
        return value

    @field_validator("headers")
    @classmethod
    def _check_headers(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 20:
            raise ValueError("A custom API can define at most 20 headers.")
        blocked = {
            "authorization",
            "api-key",
            "x-api-key",
            "x-goog-api-key",
            "host",
            "content-length",
            "transfer-encoding",
            "connection",
            "cookie",
        }
        cleaned: dict[str, str] = {}
        for name, header_value in value.items():
            key = name.strip()
            if not re.fullmatch(r"[A-Za-z0-9-]{1,64}", key):
                raise ValueError(f"Invalid custom API header name: {key!r}.")
            if key.lower() in blocked:
                raise ValueError(
                    f"Use the API key fields instead of the {key} header in the definition."
                )
            text = str(header_value).strip()
            if "\n" in text or "\r" in text or len(text) > 500:
                raise ValueError(f"Invalid value for custom API header {key}.")
            cleaned[key] = text
        return cleaned


class IntegrationSettings(BaseModel):
    github_login: str = ""
    github_read_only: bool = True


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
    proactive: ProactiveSettings = Field(default_factory=ProactiveSettings)
    audio: AudioSettings = Field(default_factory=AudioSettings)
    integrations: IntegrationSettings = Field(default_factory=IntegrationSettings)
    interface: InterfaceSettings = Field(default_factory=InterfaceSettings)
    tool_permissions: dict[str, bool] = Field(default_factory=dict)
    custom_apis: list[CustomApiSettings] = Field(default_factory=list)
    ram_floor_mb: int = Field(default=900, ge=256, le=4096)

    @field_validator("custom_apis")
    @classmethod
    def _check_custom_apis(cls, value: list[CustomApiSettings]) -> list[CustomApiSettings]:
        if len(value) > 20:
            raise ValueError("At most 20 custom APIs can be configured.")
        ids = [api.id for api in value]
        if len(ids) != len(set(ids)):
            raise ValueError("Custom API ids must be unique.")
        return value

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

    def delete(self) -> None:
        """Remove the persisted settings so the next start is a clean install."""
        self._path.unlink(missing_ok=True)

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
