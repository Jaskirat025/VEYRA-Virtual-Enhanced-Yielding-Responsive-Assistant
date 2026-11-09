"""Microphone capture with a simple silence-based stop condition.

sounddevice and numpy are optional at import time: the module only fails when
recording is actually attempted, so the rest of the application keeps working
on machines without audio devices.
"""

from __future__ import annotations

import io
import time
import wave
from array import array

from backend.audio.vad import is_speech, rms
from backend.config import AudioSettings

SAMPLE_RATE = 16_000
FRAME_SAMPLES = 480  # 30 ms


class AudioUnavailable(RuntimeError):
    """Raised when capture cannot start."""


def _sounddevice():
    try:
        import sounddevice
    except ImportError as exc:
        raise AudioUnavailable("The audio library is not installed.") from exc
    return sounddevice


def _numpy():
    try:
        import numpy
    except ImportError as exc:
        raise AudioUnavailable("NumPy is not installed.") from exc
    return numpy


def wav_bytes(samples: array) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(samples.tobytes())
    return buffer.getvalue()


def record(
    settings: AudioSettings,
    on_level=None,
) -> bytes:
    """Record until the speaker stops, then return 16 kHz mono WAV bytes."""
    sounddevice = _sounddevice()
    numpy = _numpy()

    try:
        device = settings.input_device
        stream = sounddevice.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=FRAME_SAMPLES,
            device=device,
        )
    except Exception as exc:
        raise AudioUnavailable(f"Microphone unavailable: {exc}") from exc

    collected = array("h")
    silence_started: float | None = None
    speech_started = False
    started = time.monotonic()

    try:
        with stream:
            while True:
                data, overflowed = stream.read(FRAME_SAMPLES)
                if overflowed:
                    continue
                chunk = numpy.frombuffer(data, dtype=numpy.int16)
                level = float(rms(array("h", chunk.tobytes())))
                if on_level is not None:
                    on_level(level)
                collected.extend(array("h", chunk.tobytes()))

                if is_speech(level, settings.vad_threshold):
                    speech_started = True
                    silence_started = None
                elif speech_started:
                    silence_started = silence_started or time.monotonic()
                    if (time.monotonic() - silence_started) * 1000 >= settings.silence_ms:
                        break

                if time.monotonic() - started >= settings.max_utterance_s:
                    break
                if not speech_started and time.monotonic() - started >= 6.0:
                    raise AudioUnavailable("No speech detected.")
    finally:
        stream.close()

    if not speech_started:
        raise AudioUnavailable("No speech detected.")
    return wav_bytes(collected)
