from __future__ import annotations

from backend.tools.registry import Category, ensure_tools_loaded
from backend.tools.selector import detect_categories, select_tools


def test_math_keywords_select_calc():
    registry = ensure_tools_loaded()
    selection = select_tools("Quanto fa 12 per 8?", registry, lambda name: True)
    assert Category.CALC in selection.categories
    names = {tool.name for tool in selection.tools}
    assert "calcola" in names


def test_github_keywords_select_github():
    registry = ensure_tools_loaded()
    selection = select_tools("show the latest commits of my repo", registry, lambda name: True)
    assert Category.GITHUB in selection.categories
    assert any(tool.name == "ultimi_commit" for tool in selection.tools)


def test_selection_is_small_and_includes_clarification():
    registry = ensure_tools_loaded()
    selection = select_tools("open notepad and set the volume to 30", registry, lambda name: True)
    assert len(selection.tools) <= 6
    assert "chiedi_chiarimento" in {tool.name for tool in selection.tools}


def test_custom_api_keywords_select_custom_category():
    registry = ensure_tools_loaded()
    selection = select_tools("use exa to search the web", registry, lambda name: True)
    assert Category.CUSTOM in selection.categories
    assert "chiama_api" in {tool.name for tool in selection.tools}


def test_disabled_tools_are_removed():
    registry = ensure_tools_loaded()
    selection = select_tools("calcola 2+2", registry, lambda name: name != "calcola")
    assert "calcola" not in {tool.name for tool in selection.tools}


def test_unknown_request_falls_back_to_system_and_memory():
    assert detect_categories("what can you do") == [Category.SYSTEM, Category.MEMORY]
