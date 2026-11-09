"""Sandboxed Python execution tool."""

from __future__ import annotations

from backend.tools.registry import Category, Risk, tool
from backend.tools.sandbox import run_python


@tool(category=Category.CODE, risk=Risk.DANGEROUS)
def esegui_python(codice: str, timeout: int = 20) -> str:
    """Run a short Python snippet in a sandbox and return its output.

    Use for simulations and data work when no dedicated tool fits. The sandbox
    has no network and cannot read the user's documents. Never use it to
    perform actions that a normal tool already covers.

    Args:
        codice: Python source to execute.
        timeout: maximum seconds, 3-60.
    """
    seconds = max(3, min(60, int(timeout)))
    return run_python(codice, timeout=seconds)
