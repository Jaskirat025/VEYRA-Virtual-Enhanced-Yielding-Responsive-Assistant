"""Shared fixtures: isolated data directory and runtime context."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.config import AppSettings  # noqa: E402
from backend.context import RuntimeContext, set_context  # noqa: E402
from backend.memory.db import Database  # noqa: E402
from backend.tools.registry import ensure_tools_loaded  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    yield tmp_path


@pytest.fixture
def database(tmp_path):
    return Database(tmp_path / "veyra-test.db")


@pytest.fixture
def context(database):
    ensure_tools_loaded()
    ctx = RuntimeContext(settings=AppSettings(), db=database)
    set_context(ctx)
    yield ctx
    set_context(None)
