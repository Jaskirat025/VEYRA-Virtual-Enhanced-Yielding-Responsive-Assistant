"""Gmail over IMAP/SMTP with a Google app password.

This is the local alternative to the Google OAuth client. The app password is
stored in the OS credential store through :mod:`backend.secrets`; it is never
written to the configuration file or returned by the API. Calendar remains an
OAuth-only integration.
"""

from __future__ import annotations

import contextlib
import email
import html as html_module
import imaplib
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.policy import default as default_policy
from typing import Any

from backend.context import get_context
from backend.secrets import get_secret
from backend.tools.external import wrap_external
from backend.tools.registry import ToolError

IMAP_HOST = "imap.gmail.com"
SMTP_HOST = "smtp.gmail.com"
SECRET_NAME = "gmail_app_password"


def configured() -> bool:
    """Return True when a Gmail address and app password are available."""
    try:
        address = get_context().settings.integrations.gmail_address.strip()
    except RuntimeError:
        return False
    return bool(address and get_secret(SECRET_NAME))


def _credentials() -> tuple[str, str]:
    address = get_context().settings.integrations.gmail_address.strip()
    password = (get_secret(SECRET_NAME) or "").replace(" ", "")
    if not address or not password:
        raise ToolError(
            "Gmail is not configured. Add the Google address and an app password "
            "in Settings > Accounts."
        )
    if "@" not in address or address.startswith("@") or address.endswith("@"):
        raise ToolError("The Gmail address is invalid.")
    return address, password


def _read_only() -> bool:
    return bool(get_context().settings.integrations.google_read_only)


def _open_imap() -> imaplib.IMAP4_SSL:
    address, password = _credentials()
    try:
        client = imaplib.IMAP4_SSL(
            IMAP_HOST,
            993,
            ssl_context=ssl.create_default_context(),
        )
        client.login(address, password)
    except (imaplib.IMAP4.error, OSError) as exc:
        raise ToolError("Gmail login failed. Check the address and app password.") from exc
    return client


def _close(client: imaplib.IMAP4_SSL) -> None:
    with contextlib.suppress(Exception):
        client.logout()


def _search_uids(client: imaplib.IMAP4_SSL, query: str, limit: int) -> list[bytes]:
    status, _ = client.select("INBOX", readonly=True)
    if status != "OK":
        raise ToolError("Could not open the Gmail inbox.")

    if query.strip():
        escaped = query.strip().replace('"', '\\"')
        status, data = client.uid("SEARCH", None, "X-GM-RAW", f'"{escaped}"')
    else:
        status, data = client.uid("SEARCH", None, "ALL")

    if status != "OK":
        raise ToolError("Gmail search failed.")

    first = data[0] if data else b""
    if isinstance(first, bytes):
        uids = first.split()
    elif isinstance(first, str):
        uids = first.encode("ascii", "replace").split()
    else:
        uids = []
    return uids[-limit:][::-1]


def _fetch(client: imaplib.IMAP4_SSL, uid: bytes, section: str) -> bytes:
    status, data = client.uid("FETCH", uid, f"(BODY.PEEK[{section}])")
    if status != "OK":
        raise ToolError("Could not read the Gmail message.")
    chunks = [
        bytes(part[1])
        for part in data or []
        if isinstance(part, tuple) and len(part) >= 2 and isinstance(part[1], (bytes, bytearray))
    ]
    if not chunks:
        raise ToolError("Gmail returned an empty message.")
    return b"".join(chunks)


def _header(message: Any, name: str) -> str:
    value = message.get(name)
    return str(value).strip() if value else ""


def _extract_body(message: Any) -> str:
    part = None
    if hasattr(message, "get_body"):
        part = message.get_body(preferencelist=("plain", "html"))
    if part is None:
        payload = message.get_payload(decode=True)
        return payload.decode("utf-8", errors="replace").strip() if payload else ""

    try:
        content = part.get_content()
    except (KeyError, LookupError, ValueError):
        payload = part.get_payload(decode=True) or b""
        content = payload.decode(part.get_content_charset() or "utf-8", errors="replace")

    text = str(content)
    if part.get_content_subtype() == "html":
        text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = html_module.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:2500]


def search_messages(query: str, limit: int = 5) -> str:
    """Search Gmail and return message ids, subjects, senders and dates."""
    count = max(1, min(10, int(limit)))
    client = _open_imap()
    try:
        uids = _search_uids(client, query, count)
        if not uids:
            return "No messages matched."
        lines: list[str] = []
        for uid in uids:
            raw = _fetch(client, uid, "HEADER.FIELDS (SUBJECT FROM DATE)")
            message = email.message_from_bytes(raw, policy=default_policy)
            lines.append(
                f"id={uid.decode('ascii', 'replace')} | "
                f"{_header(message, 'Subject') or '(no subject)'} | "
                f"{_header(message, 'From')} | {_header(message, 'Date')}"
            )
    except ToolError:
        raise
    except (imaplib.IMAP4.error, OSError, ValueError) as exc:
        raise ToolError("Gmail search failed. Try again.") from exc
    finally:
        _close(client)
    return wrap_external("gmail", "\n".join(lines))


def read_message(message_id: str) -> str:
    """Read one Gmail message by the id returned from search_messages."""
    uid = message_id.strip()
    if not uid.isdigit():
        raise ToolError("The Gmail message id is invalid.")
    client = _open_imap()
    try:
        status, _ = client.select("INBOX", readonly=True)
        if status != "OK":
            raise ToolError("Could not open the Gmail inbox.")
        raw = _fetch(client, uid.encode("ascii"), "")
        message = email.message_from_bytes(raw, policy=default_policy)
        body = _extract_body(message) or "(no plain-text body)"
        content = (
            f"Subject: {_header(message, 'Subject') or '(no subject)'}\n"
            f"From: {_header(message, 'From')}\n"
            f"Date: {_header(message, 'Date')}\n\n{body}"
        )
    except ToolError:
        raise
    except (imaplib.IMAP4.error, OSError, ValueError) as exc:
        raise ToolError("Could not read the Gmail message.") from exc
    finally:
        _close(client)
    return wrap_external("gmail", content)


def send_message(recipient: str, subject: str, body: str) -> str:
    """Send plain-text mail through Gmail SMTP after the write check."""
    if _read_only():
        raise ToolError("Google is in read-only mode. Enable writing in Settings > Accounts.")
    address, password = _credentials()
    recipient = recipient.strip()
    if "@" not in recipient:
        raise ToolError("The recipient address is invalid.")
    if not body.strip():
        raise ToolError("The message body is empty.")

    message = EmailMessage()
    message["To"] = recipient
    message["From"] = address
    message["Subject"] = subject.strip()
    message.set_content(body)

    try:
        with smtplib.SMTP_SSL(
            SMTP_HOST,
            465,
            timeout=30,
            context=ssl.create_default_context(),
        ) as smtp:
            smtp.login(address, password)
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise ToolError(f"Sending failed: {exc}") from exc
    return f"Message sent to {recipient}."
