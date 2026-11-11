"""Filesystem locations for Veyra.

All user data lives under the user's application-data directory, never inside
the repository or the installation folder. Nothing here is hard-coded to a
specific user or machine.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = "Veyra"


def app_data_root() -> Path:
    """Return the per-user data root for the current platform.

    Windows uses %APPDATA%, macOS uses ~/Library/Application Support and other
    platforms follow the XDG base-directory spec.
    """
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        if not base:
            raise RuntimeError("APPDATA is not set; cannot locate the Veyra data folder")
        return Path(base)

    if os.uname().sysname == "Darwin":  # pragma: no cover - Windows is the target
        return Path.home() / "Library" / "Application Support"

    base = os.environ.get("XDG_CONFIG_HOME")
    return Path(base) if base else Path.home() / ".config"


def app_data_dir() -> Path:
    """Return the Veyra data directory, creating it if needed."""
    path = app_data_root() / APP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_within(path: Path, root: Path) -> bool:
    """Return True when ``path`` is inside ``root`` (not a sibling prefix)."""
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def config_path() -> Path:
    return app_data_dir() / "config.json"


def db_path() -> Path:
    return app_data_dir() / "veyra.db"


def logs_dir() -> Path:
    path = app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def models_dir() -> Path:
    path = app_data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def voices_dir() -> Path:
    path = app_data_dir() / "voices"
    path.mkdir(parents=True, exist_ok=True)
    return path


def charts_dir() -> Path:
    path = app_data_dir() / "charts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def credentials_dir() -> Path:
    path = app_data_dir() / "credentials"
    path.mkdir(parents=True, exist_ok=True)
    return path


def temp_dir() -> Path:
    path = app_data_dir() / "tmp"
    path.mkdir(parents=True, exist_ok=True)
    return path
