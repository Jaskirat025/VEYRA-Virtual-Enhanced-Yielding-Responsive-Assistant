"""Lightweight energy-based voice activity detection."""

from __future__ import annotations

from array import array
from math import sqrt


def rms(samples: array) -> float:
    if not samples:
        return 0.0
    total = 0.0
    for value in samples:
        total += float(value) * float(value)
    return sqrt(total / len(samples))


def normalise_rms(value: float) -> float:
    """Map 16-bit PCM RMS to a rough 0..1 level for the interface."""
    return max(0.0, min(1.0, value / 8000.0))


def is_speech(value: float, threshold: float) -> bool:
    return value >= threshold
