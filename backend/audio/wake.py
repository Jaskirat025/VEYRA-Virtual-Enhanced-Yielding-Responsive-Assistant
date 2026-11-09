"""Wake-word detection with openWakeWord (no account or API key required).

A custom phrase such as "Hey Veyra" needs a trained openWakeWord model. If no
model path is configured, detection is unavailable and the interface says so
instead of pretending to listen.
"""

from __future__ import annotations

import time
from pathlib import Path

from backend.config import AudioSettings

FRAME = 1280  # 80 ms at 16 kHz, as expected by openWakeWord
THRESHOLD = 0.55


def available(settings: AudioSettings) -> bool:
    if settings.wake_engine != "openwakeword":
        return False
    path = Path(settings.wake_model_path).expanduser()
    if not path.is_file():
        return False
    try:
        import openwakeword  # noqa: F401
        import sounddevice  # noqa: F401
    except ImportError:
        return False
    return True


def listen(settings: AudioSettings, stop, on_detect) -> None:
    """Blocking loop; returns when ``stop`` is set."""
    if not available(settings):
        raise RuntimeError("Wake word is not configured.")

    import numpy as np
    import sounddevice as sd
    from openwakeword.model import Model

    model = Model(wakeword_models=[str(Path(settings.wake_model_path).expanduser())])
    stream = sd.InputStream(
        samplerate=16_000,
        channels=1,
        dtype="int16",
        blocksize=FRAME,
        device=settings.input_device,
    )

    with stream:
        while not stop.is_set():
            data, overflowed = stream.read(FRAME)
            if overflowed:
                continue
            scores = model.predict(np.frombuffer(data, dtype=np.int16))
            if scores and max(scores.values()) >= THRESHOLD:
                model.reset()
                on_detect()
                time.sleep(0.5)
