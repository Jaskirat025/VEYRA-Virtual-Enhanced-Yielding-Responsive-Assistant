"""Explicit sharing helpers for messaging services."""

from __future__ import annotations

import re
import webbrowser
from urllib.parse import quote

from backend.tools.registry import Category, Risk, ToolError, tool


@tool(category=Category.COMMUNICATION, risk=Risk.CONFIRM, tags=("external", "whatsapp"))
def condividi_whatsapp(numero: str, testo: str) -> str:
    """Open WhatsApp with a prefilled message for a phone number.

    Use when the user asks to prepare a WhatsApp message. This opens the
    official wa.me share page; the user reviews and presses Send in WhatsApp.
    It does not read the WhatsApp inbox and does not send automatically.

    Args:
        numero: international phone number, digits with an optional + prefix.
        testo: message to prefill, at most 1000 characters.
    """
    digits = re.sub(r"\D", "", numero)
    if not 8 <= len(digits) <= 15:
        raise ToolError("Provide a phone number with country code, for example +39...")
    message = testo.strip()
    if not message:
        raise ToolError("The WhatsApp message is empty.")
    if len(message) > 1000:
        raise ToolError("The WhatsApp message is too long (max 1000 characters).")

    url = f"https://wa.me/{digits}?text={quote(message, safe='')}"
    try:
        opened = webbrowser.open(url)
    except Exception as exc:
        raise ToolError("Could not open WhatsApp in the default browser.") from exc
    if not opened:
        raise ToolError("Could not open WhatsApp in the default browser.")
    return "WhatsApp opened with the message ready. Review it and press Send there."
