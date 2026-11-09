"""Runtime services shared by tools and the API layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.config import AppSettings
from backend.memory.db import Database


@dataclass
class RuntimeContext:
    settings: AppSettings
    db: Database
    extras: dict[str, Any] = field(default_factory=dict)


_context: RuntimeContext | None = None


def set_context(context: RuntimeContext | None) -> None:
    global _context
    _context = context


def get_context() -> RuntimeContext:
    if _context is None:
        raise RuntimeError("Runtime context is not initialised")
    return _context
