"""Desktop automation tools. All of them are destructive enough to confirm."""

from __future__ import annotations

import os

from backend.tools.registry import Category, Risk, ToolError, tool


def _pyautogui():
    if os.name != "nt":
        raise ToolError("Desktop automation is available on Windows only.")
    try:
        import pyautogui
    except ImportError as exc:
        raise ToolError("pyautogui is not installed.") from exc
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    return pyautogui


@tool(category=Category.UI, risk=Risk.CONFIRM, tags=("desktop_control",))
def clicca(x: int, y: int, doppio: bool = False) -> str:
    """Click at absolute screen coordinates.

    Use only when the user asks to click somewhere on screen. Prefer
    `scorciatoia` when a keyboard shortcut is enough.

    Args:
        x: horizontal pixel coordinate.
        y: vertical pixel coordinate.
        doppio: true for a double click.
    """
    pyautogui = _pyautogui()
    width, height = pyautogui.size()
    if not (0 <= x <= width and 0 <= y <= height):
        raise ToolError(f"Coordinates are outside the screen ({width}x{height}).")
    pyautogui.doubleClick(x, y) if doppio else pyautogui.click(x, y)
    return f"Clicked at {x},{y}."


@tool(category=Category.UI, risk=Risk.CONFIRM, tags=("desktop_control",))
def scrivi(testo: str) -> str:
    """Type text into the currently focused window.

    Use when the user asks to type something. The text is typed verbatim.

    Args:
        testo: text to type.
    """
    if not testo:
        raise ToolError("No text to type.")
    _pyautogui().typewrite(testo, interval=0.01)
    return f"Typed {len(testo)} characters."


@tool(category=Category.UI, risk=Risk.CONFIRM, tags=("desktop_control",))
def scorciatoia(tasti: str) -> str:
    """Press a keyboard shortcut such as "ctrl+s" or "alt+tab".

    Use for shortcuts instead of clicking through menus.

    Args:
        tasti: keys joined by "+", for example "ctrl+shift+esc".
    """
    parts = [part.strip().lower() for part in tasti.split("+") if part.strip()]
    if not parts or len(parts) > 5:
        raise ToolError("Provide a shortcut such as 'ctrl+s'.")
    _pyautogui().hotkey(*parts)
    return f"Pressed {'+'.join(parts)}."
