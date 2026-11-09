from __future__ import annotations

import pytest
from backend.integrations import gmail_local
from backend.tools.registry import ToolError

ACCOUNT = "demo" + "@" + "example.invalid"
PASSWORD = "app-password"


def raw_message() -> bytes:
    return (
        b"Subject: Ciao\n"
        b"From: Demo sender\n"
        b"Date: Mon, 09 Nov 2026 10:00:00 +0000\n"
        b"Content-Type: text/plain; charset=utf-8\n"
        b"\n"
        b"Testo del messaggio.\n"
    )


class FakeIMAP:
    instances: list[FakeIMAP] = []

    def __init__(self, *args, **kwargs):
        self.commands: list[tuple] = []
        self.logged_out = False
        FakeIMAP.instances.append(self)

    def login(self, address, password):
        self.commands.append(("LOGIN", address, password))

    def select(self, mailbox, readonly=False):
        self.commands.append(("SELECT", mailbox, readonly))
        return "OK", [b"1"]

    def uid(self, command, *args):
        self.commands.append((command, args))
        if command == "SEARCH":
            return "OK", [b"2 1"]
        if command == "FETCH":
            section = args[1] if len(args) > 1 else ""
            if "HEADER" in section:
                return "OK", [(b"header", raw_message().split(b"\n\n")[0] + b"\n\n"), b")"]
            return "OK", [(b"body", raw_message()), b")"]
        return "OK", [b""]

    def logout(self):
        self.logged_out = True


class FakeSMTP:
    instances: list[FakeSMTP] = []

    def __init__(self, *args, **kwargs):
        self.commands: list[tuple] = []
        self.message = None
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def login(self, address, password):
        self.commands.append(("LOGIN", address, password))

    def send_message(self, message):
        self.message = message


def test_search_and_read_use_local_imap(monkeypatch):
    FakeIMAP.instances.clear()
    monkeypatch.setattr(gmail_local, "_credentials", lambda: (ACCOUNT, PASSWORD))
    monkeypatch.setattr(gmail_local.imaplib, "IMAP4_SSL", FakeIMAP)

    found = gmail_local.search_messages("from:demo", 5)
    assert "id=1" in found
    assert "Ciao" in found
    assert "<dati_esterni fonte='gmail'>" in found

    message = gmail_local.read_message("1")
    assert "Testo del messaggio." in message
    assert "<dati_esterni fonte='gmail'>" in message
    assert FakeIMAP.instances[1].logged_out is True
    assert ("SELECT", "INBOX", True) in FakeIMAP.instances[1].commands

    commands = FakeIMAP.instances[0].commands
    assert ("SELECT", "INBOX", True) in commands
    search = next(entry for entry in commands if entry[0] == "SEARCH")
    assert "X-GM-RAW" in search[1]


def test_send_uses_smtp_and_respects_read_only(monkeypatch):
    FakeSMTP.instances.clear()
    monkeypatch.setattr(gmail_local, "_credentials", lambda: (ACCOUNT, PASSWORD))
    monkeypatch.setattr(gmail_local, "_read_only", lambda: False)
    monkeypatch.setattr(gmail_local.smtplib, "SMTP_SSL", FakeSMTP)

    result = gmail_local.send_message("recipient" + "@" + "invalid", "Oggetto", "Corpo")
    assert "Message sent" in result
    assert FakeSMTP.instances[0].message["Subject"] == "Oggetto"
    assert FakeSMTP.instances[0].message.get_content().strip() == "Corpo"

    monkeypatch.setattr(gmail_local, "_read_only", lambda: True)
    with pytest.raises(ToolError, match="read-only"):
        gmail_local.send_message("recipient" + "@" + "invalid", "Oggetto", "Corpo")


def test_gmail_tools_route_to_local_mode(monkeypatch):
    from backend.tools.builtin import google

    monkeypatch.setattr(gmail_local, "configured", lambda: True)
    monkeypatch.setattr(
        gmail_local, "search_messages", lambda query, limit: f"local:{query}:{limit}"
    )
    monkeypatch.setattr(gmail_local, "read_message", lambda message_id: f"read:{message_id}")

    assert google.cerca_mail("from:demo", 3) == "local:from:demo:3"
    assert google.leggi_mail("7") == "read:7"
