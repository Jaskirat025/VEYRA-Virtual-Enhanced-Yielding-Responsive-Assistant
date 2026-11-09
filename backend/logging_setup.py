"""Logging configuration with secret redaction.

Logs are written to the per-user logs directory and rotated. Anything that
looks like a credential is redacted before it reaches a handler.
"""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler

from backend.paths import logs_dir

_REDACTIONS = (
    (re.compile(r"(sk-[A-Za-z0-9_-]{8,})"), "[redacted-key]"),
    (re.compile(r"(ghp_[A-Za-z0-9]{8,})"), "[redacted-token]"),
    (re.compile(r"(AIza[0-9A-Za-z_-]{10,})"), "[redacted-key]"),
    (re.compile(r"(?i)(authorization:\s*bearer\s+)\S+"), r"\1[redacted]"),
    (re.compile(r"(?i)(token=)[^&\s]+"), r"\1[redacted]"),
)


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        for pattern, replacement in _REDACTIONS:
            message = pattern.sub(replacement, message)
        record.msg = message
        record.args = ()
        return True


def configure_logging(level: str = "INFO", console: bool = True) -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    redaction = RedactionFilter()

    try:
        file_handler = RotatingFileHandler(
            logs_dir() / "veyra.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(redaction)
        root.addHandler(file_handler)
    except OSError:
        # Logging must never prevent startup.
        pass

    if console:
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        stream.addFilter(redaction)
        root.addHandler(stream)
