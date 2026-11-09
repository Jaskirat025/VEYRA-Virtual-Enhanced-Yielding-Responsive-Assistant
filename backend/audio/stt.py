"""Speech-to-text with faster-whisper, loaded lazily and unloaded on demand."""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path

from backend.config import AudioSettings


class SpeechUnavailable(RuntimeError):
    """Raised when transcription cannot run."""


_model = None
_model_key: tuple[str, str] | None = None
_lock = threading.Lock()


def available() -> bool:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def _load(settings: AudioSettings):
    global _model, _model_key
    key = (settings.stt_model, settings.stt_compute_type)
    with _lock:
        if _model is not None and _model_key == key:
            return _model
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise SpeechUnavailable("faster-whisper is not installed.") from exc
        try:
            _model = WhisperModel(
                settings.stt_model,
                device="cpu",
                compute_type=settings.stt_compute_type,
            )
            _model_key = key
        except Exception as exc:
            raise SpeechUnavailable(f"Could not load the speech model: {exc}") from exc
        return _model


def unload() -> None:
    global _model, _model_key
    with _lock:
        _model = None
        _model_key = None


def transcribe(wav: bytes, settings: AudioSettings, language: str | None = None) -> str:
    model = _load(settings)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        handle.write(wav)
        path = Path(handle.name)
    try:
        segments, _info = model.transcribe(
            str(path), language=language, vad_filter=True, beam_size=1
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
    except Exception as exc:
        raise SpeechUnavailable(f"Transcription failed: {exc}") from exc
    finally:
        path.unlink(missing_ok=True)
    if not text:
        raise SpeechUnavailable("I did not catch that.")
    return text
