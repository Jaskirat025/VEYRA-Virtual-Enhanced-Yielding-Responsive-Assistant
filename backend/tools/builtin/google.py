"""Google Gmail and Calendar tools.

The OAuth client belongs to the user; the refresh token is stored in Windows
Credential Manager. Read-only is the default and writing must be enabled.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from email.mime.text import MIMEText

from backend.context import get_context
from backend.secrets import get_secret
from backend.tools.external import wrap_external
from backend.tools.registry import Category, Risk, ToolError, tool


def _build(service: str, version: str):
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise ToolError("Google support is not installed.") from exc

    raw = get_secret("google_token_json")
    if not raw:
        raise ToolError("Google is not connected. Sign in from Settings > Accounts.")
    try:
        credentials = Credentials.from_authorized_user_info(eval(raw))  # noqa: S307 - stored JSON
    except Exception as exc:
        raise ToolError("The stored Google token is invalid. Sign in again.") from exc
    try:
        return build(service, version, credentials=credentials, cache_discovery=False)
    except Exception as exc:
        raise ToolError(f"Could not reach Google: {exc}") from exc


def _require_write(service: str) -> None:
    settings = get_context().settings
    read_only = settings.integrations.google_read_only
    if read_only:
        raise ToolError(f"Google {service} is read-only. Enable writing in Settings > Accounts.")


@tool(category=Category.GOOGLE, risk=Risk.SAFE, tags=("external",))
def cerca_mail(query: str = "", limite: int = 5) -> str:
    """Search Gmail and return matching message summaries.

    Use when the user asks about mail. The query uses Gmail search syntax, for
    example "newer_than:1d" or "from:someone".

    Args:
        query: Gmail search query; empty returns the latest messages.
        limite: number of messages, 1-10.
    """
    service = _build("gmail", "v1")
    count = max(1, min(10, int(limite)))
    try:
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query.strip(), maxResults=count)
            .execute()
        )
        messages = response.get("messages", [])
        lines = []
        for item in messages:
            detail = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=item["id"],
                    format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                )
                .execute()
            )
            headers = {
                header["name"]: header["value"]
                for header in detail.get("payload", {}).get("headers", [])
            }
            lines.append(
                f"id={item['id']} | {headers.get('Subject', '(no subject)')} | "
                f"{headers.get('From', '')} | {headers.get('Date', '')}"
            )
    except Exception as exc:
        raise ToolError(f"Gmail search failed: {exc}") from exc

    if not lines:
        return "No messages matched."
    return wrap_external("gmail", "\n".join(lines))


def _extract_body(payload: dict) -> str:
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    for part in payload.get("parts", []) or []:
        text = _extract_body(part)
        if text:
            return text
    return ""


@tool(category=Category.GOOGLE, risk=Risk.SAFE, tags=("external",))
def leggi_mail(message_id: str) -> str:
    """Read one Gmail message by id.

    Use after searching mail, when the user wants the content of a message.

    Args:
        message_id: id returned by cerca_mail.
    """
    if not message_id.strip():
        raise ToolError("The message id is empty.")
    service = _build("gmail", "v1")
    try:
        detail = (
            service.users()
            .messages()
            .get(userId="me", id=message_id.strip(), format="full")
            .execute()
        )
    except Exception as exc:
        raise ToolError(f"Could not read the message: {exc}") from exc

    headers = {
        header["name"]: header["value"] for header in detail.get("payload", {}).get("headers", [])
    }
    body = _extract_body(detail.get("payload", {}))[:2500]
    content = (
        f"Subject: {headers.get('Subject', '(no subject)')}\n"
        f"From: {headers.get('From', '')}\nDate: {headers.get('Date', '')}\n\n{body}"
    )
    return wrap_external("gmail", content)


@tool(category=Category.GOOGLE, risk=Risk.SAFE)
def bozza_mail(destinatario: str, oggetto: str, corpo: str) -> str:
    """Create a Gmail draft without sending it.

    Use when the user wants a reply or message prepared but not sent.

    Args:
        destinatario: recipient e-mail address.
        oggetto: subject line.
        corpo: plain-text body.
    """
    _require_write("Gmail")
    if "@" not in destinatario:
        raise ToolError("The recipient address is invalid.")
    service = _build("gmail", "v1")
    message = MIMEText(corpo, "plain", "utf-8")
    message["to"] = destinatario.strip()
    message["subject"] = oggetto.strip()
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
    try:
        draft = (
            service.users()
            .drafts()
            .create(userId="me", body={"message": {"raw": encoded}})
            .execute()
        )
    except Exception as exc:
        raise ToolError(f"Could not create the draft: {exc}") from exc
    return f"Draft created (id {draft.get('id')}). Nothing was sent."


@tool(category=Category.GOOGLE, risk=Risk.CONFIRM)
def invia_mail(destinatario: str, oggetto: str, corpo: str) -> str:
    """Send an e-mail through Gmail.

    Use only when the user explicitly asks to send the message. Sending is
    irreversible, so confirmation is required.

    Args:
        destinatario: recipient e-mail address.
        oggetto: subject line.
        corpo: plain-text body.
    """
    _require_write("Gmail")
    if "@" not in destinatario:
        raise ToolError("The recipient address is invalid.")
    service = _build("gmail", "v1")
    message = MIMEText(corpo, "plain", "utf-8")
    message["to"] = destinatario.strip()
    message["subject"] = oggetto.strip()
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
    try:
        service.users().messages().send(userId="me", body={"raw": encoded}).execute()
    except Exception as exc:
        raise ToolError(f"Sending failed: {exc}") from exc
    return f"Message sent to {destinatario.strip()}."


def _calendar():
    _require_write("Calendar")
    return _build("calendar", "v3")


def _format_event(event: dict) -> str:
    start = event.get("start", {})
    moment = start.get("dateTime") or start.get("date") or ""
    return f"{moment} | {event.get('summary', '(no title)')}"


@tool(category=Category.GOOGLE, risk=Risk.SAFE, tags=("external",))
def eventi_oggi() -> str:
    """List today's calendar events.

    Use when the user asks what is scheduled today.
    """
    service = _build("calendar", "v3")
    now = datetime.now(UTC)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    try:
        response = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
    except Exception as exc:
        raise ToolError(f"Could not read the calendar: {exc}") from exc
    events = response.get("items", [])
    if not events:
        return "No events today."
    return wrap_external("calendar", "\n".join(_format_event(event) for event in events[:20]))


@tool(category=Category.GOOGLE, risk=Risk.SAFE, tags=("external",))
def eventi_range(inizio: str, fine: str) -> str:
    """List calendar events between two ISO dates.

    Use for questions about a period, such as next week.

    Args:
        inizio: ISO date or datetime, for example "2026-11-10".
        fine: ISO date or datetime, for example "2026-11-17".
    """
    service = _build("calendar", "v3")
    try:
        start = datetime.fromisoformat(inizio.strip())
        end = datetime.fromisoformat(fine.strip())
    except ValueError as exc:
        raise ToolError("Dates must be ISO, for example 2026-11-10.") from exc
    try:
        response = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                maxResults=50,
            )
            .execute()
        )
    except Exception as exc:
        raise ToolError(f"Could not read the calendar: {exc}") from exc
    events = response.get("items", [])
    if not events:
        return "No events in that period."
    return wrap_external("calendar", "\n".join(_format_event(event) for event in events[:50]))


@tool(category=Category.GOOGLE, risk=Risk.CONFIRM)
def crea_evento(titolo: str, inizio: str, fine: str) -> str:
    """Create a calendar event.

    Use only when the user asks to schedule something. Confirmation is
    required because an event can notify other people.

    Args:
        titolo: event title.
        inizio: ISO datetime, for example "2026-11-10T15:00:00".
        fine: ISO datetime, for example "2026-11-10T16:00:00".
    """
    _require_write("Calendar")
    service = _build("calendar", "v3")
    try:
        start = datetime.fromisoformat(inizio.strip())
        end = datetime.fromisoformat(fine.strip())
    except ValueError as exc:
        raise ToolError("Dates must be ISO datetimes.") from exc
    if end <= start:
        raise ToolError("The end must be after the start.")
    try:
        created = (
            service.events()
            .insert(
                calendarId="primary",
                body={
                    "summary": titolo.strip(),
                    "start": {"dateTime": start.isoformat()},
                    "end": {"dateTime": end.isoformat()},
                },
            )
            .execute()
        )
    except Exception as exc:
        raise ToolError(f"Could not create the event: {exc}") from exc
    return f"Event created: {created.get('htmlLink', titolo)}"
