"""Meta tools that do not touch the system."""

from __future__ import annotations

from backend.tools.registry import Category, Risk, ToolError, tool


@tool(category=Category.META, risk=Risk.SAFE)
def chiedi_chiarimento(domanda: str) -> str:
    """Ask the user for missing information instead of guessing.

    Use when a required detail (recipient, file, date, target app) is unknown.

    Args:
        domanda: the single question to ask the user.
    """
    question = domanda.strip()
    if not question:
        raise ToolError("The clarification question is empty.")
    return f"Clarification requested from the user: {question[:300]}"
