"""Text-to-speech: Piper through its Python package, with a pyttsx3 fallback."""

from __future__ import annotations

import os
import tempfile
import threading
import wave
from pathlib import Path

from backend.config import VoiceSettings
from backend.paths import voices_dir

DEFAULT_VOICES: dict[str, tuple[str, str]] = {
    "en": ("en_US-lessac-medium", "en/en_US/lessac/medium"),
    "it": ("it_IT-paola-medium", "it/it_IT/paola/medium"),
    "zh": ("zh_CN-huayan-medium", "zh/zh_CN/huayan/medium"),
}


class SpeechUnavailable(RuntimeError):
    """Raised when no speech engine can produce audio."""


def voice_name(language: str) -> str:
    return DEFAULT_VOICES.get(language, DEFAULT_VOICES["en"])[0]


def voice_relative_path(language: str) -> str:
    return DEFAULT_VOICES.get(language, DEFAULT_VOICES["en"])[1]


def default_voice_path(language: str) -> Path:
    return voices_dir() / f"{voice_name(language)}.onnx"


def voice_path(settings: VoiceSettings, language: str = "en") -> Path:
    configured = settings.piper_voice.strip()
    if configured:
        return Path(configured).expanduser()
    return default_voice_path(language)


def piper_available(settings: VoiceSettings, language: str = "en") -> bool:
    if settings.engine != "piper":
        return False
    try:
        import piper  # noqa: F401
    except ImportError:
        return False
    return voice_path(settings, language).is_file()


def _piper(settings: VoiceSettings, language: str, text: str) -> bytes:
    voice_file = voice_path(settings, language)
    if not voice_file.is_file():
        raise SpeechUnavailable("The Piper voice model is missing.")

    try:
        from piper import PiperVoice
    except ImportError as exc:
        raise SpeechUnavailable("The Piper speech package is not installed.") from exc

    with tempfile.TemporaryDirectory(prefix="veyra-tts-") as folder:
        output = Path(folder) / "speech.wav"
        try:
            voice = PiperVoice.load(str(voice_file))
            with wave.open(str(output), "wb") as wav_file:
                voice.synthesize_wav(text, wav_file)
        except Exception as exc:
            raise SpeechUnavailable(f"Piper could not synthesise the answer: {exc}") from exc
        if not output.exists():
            raise SpeechUnavailable("Piper did not produce an audio file.")
        return output.read_bytes()


def _pyttsx3(settings: VoiceSettings, text: str) -> bytes:
    try:
        import pyttsx3
    except ImportError as exc:
        raise SpeechUnavailable("No speech engine is installed.") from exc

    with tempfile.TemporaryDirectory(prefix="veyra-tts-") as folder:
        output = Path(folder) / "speech.wav"
        error: list[str] = []

        def run() -> None:
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", settings.rate)
                engine.setProperty("volume", settings.volume)
                engine.save_to_file(text, str(output))
                engine.runAndWait()
                engine.stop()
            except Exception as exc:  # pragma: no cover - Windows SAPI
                error.append(str(exc))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        thread.join(timeout=30)
        if error or not output.exists():
            raise SpeechUnavailable("The system speech engine could not synthesise the answer.")
        return output.read_bytes()


def synthesize(text: str, settings: VoiceSettings, language: str = "en") -> bytes:
    clean = text.strip()
    if not clean:
        raise SpeechUnavailable("There is nothing to say.")
    # Keep spoken answers short even if the model ignores the instruction.
    if len(clean) > 1200:
        clean = clean[:1200].rsplit(" ", 1)[0] + "."

    if settings.engine == "piper" and piper_available(settings, language):
        return _piper(settings, language, clean)
    if os.name == "nt" or settings.engine == "pyttsx3":
        return _pyttsx3(settings, clean)
    raise SpeechUnavailable("No speech engine is available on this system.")
