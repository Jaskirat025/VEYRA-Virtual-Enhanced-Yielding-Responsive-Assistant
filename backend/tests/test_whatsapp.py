from __future__ import annotations

import pytest
from backend.tools.builtin.communication import condividi_whatsapp
from backend.tools.registry import Category, ToolError
from backend.tools.selector import detect_categories


def test_share_opens_a_prefilled_wa_me_link(monkeypatch):
    opened: list[str] = []
    monkeypatch.setattr(
        "backend.tools.builtin.communication.webbrowser.open",
        lambda url: opened.append(url) or True,
    )

    result = condividi_whatsapp("+39 333 123 4567", "Ciao mondo")
    assert "wa.me/393331234567" in opened[0]
    assert "Ciao%20mondo" in opened[0]
    assert "press Send" in result


def test_share_rejects_invalid_numbers():
    with pytest.raises(ToolError):
        condividi_whatsapp("123", "Ciao")


def test_whatsapp_selects_the_communication_category():
    assert Category.COMMUNICATION in detect_categories("manda un whatsapp a Marco")
