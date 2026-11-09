"""End-to-end voice capture: record, transcribe, return text."""

from __future__ import annotations

from collections.abc import Callable

from backend.audio.recorder import record
from backend.audio.stt import transcribe
from backend.config import AppSettings


def listen_once(
    settings: AppSettings,
    language: str | None = None,
    on_level: Callable[[float], None] | None = None,
) -> str:
    wav = record(settings.audio, on_level=on_level)
    return transcribe(wav, settings.audio, language=language)
