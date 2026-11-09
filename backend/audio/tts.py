"""Text-to-speech: Piper with a pyttsx3 fallback."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from backend.config import VoiceSettings


class SpeechUnavailable(RuntimeError):
    """Raised when no speech engine can produce audio."""


def piper_available(settings: VoiceSettings) -> bool:
    return bool(
        shutil.which("piper")
        and settings.piper_voice
        and Path(settings.piper_voice).expanduser().is_file()
    )


def _piper(settings: VoiceSettings, text: str) -> bytes:
    binary = shutil.which("piper")
    voice = Path(settings.piper_voice).expanduser()
    if not binary or not voice.is_file():
        raise SpeechUnavailable("Piper or its voice model is missing.")

    with tempfile.TemporaryDirectory(prefix="veyra-tts-") as folder:
        output = Path(folder) / "speech.wav"
        try:
            completed = subprocess.run(
                [binary, "--model", str(voice), "--output_file", str(output)],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SpeechUnavailable(f"Piper failed: {exc}") from exc
        if completed.returncode != 0 or not output.exists():
            raise SpeechUnavailable("Piper could not synthesise the answer.")
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


def synthesize(text: str, settings: VoiceSettings) -> bytes:
    clean = text.strip()
    if not clean:
        raise SpeechUnavailable("There is nothing to say.")
    # Keep spoken answers short even if the model ignores the instruction.
    if len(clean) > 1200:
        clean = clean[:1200].rsplit(" ", 1)[0] + "."

    if settings.engine == "piper" and piper_available(settings):
        return _piper(settings, clean)
    if os.name == "nt" or settings.engine == "pyttsx3":
        return _pyttsx3(settings, clean)
    raise SpeechUnavailable("No speech engine is available on this system.")
