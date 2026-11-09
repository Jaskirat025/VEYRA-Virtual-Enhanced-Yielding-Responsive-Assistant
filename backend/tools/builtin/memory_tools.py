"""Memory tools: notes, timers and alarms."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.context import get_context
from backend.tools.registry import Category, Risk, ToolError, tool


@tool(category=Category.MEMORY, risk=Risk.SAFE)
def salva_nota(titolo: str, testo: str) -> str:
    """Save a note in the local database.

    Use when the user asks to remember something.

    Args:
        titolo: short title for the note.
        testo: note content.
    """
    title = titolo.strip()
    if not title:
        raise ToolError("The note title is empty.")
    note_id = get_context().db.save_note(title[:200], testo.strip())
    return f"Note #{note_id} saved."


@tool(category=Category.MEMORY, risk=Risk.SAFE)
def cerca_note(query: str, limite: int = 5) -> str:
    """Search saved notes by text.

    Use when the user asks what was noted about something.

    Args:
        query: text to look for.
        limite: maximum number of notes, 1-20.
    """
    if not query.strip():
        raise ToolError("The search text is empty.")
    notes = get_context().db.search_notes(query.strip(), limit=max(1, min(20, int(limite))))
    if not notes:
        return "No notes matched."
    return "\n".join(f"#{note['id']} {note['title']}: {note['body'][:200]}" for note in notes)


@tool(category=Category.MEMORY, risk=Risk.SAFE)
def timer(secondi: int, etichetta: str = "") -> str:
    """Start a countdown timer.

    Use when the user asks to be reminded after a delay.

    Args:
        secondi: duration in seconds, 1-86400.
        etichetta: optional label for the timer.
    """
    seconds = int(secondi)
    if not 1 <= seconds <= 86_400:
        raise ToolError("The timer must be between 1 second and 24 hours.")
    fire_at = (datetime.now(UTC) + timedelta(seconds=seconds)).isoformat(timespec="seconds")
    get_context().db.add_timer(etichetta.strip() or "timer", fire_at)
    return f"Timer set for {seconds} seconds."


@tool(category=Category.MEMORY, risk=Risk.SAFE)
def sveglia(ora: str, etichetta: str = "") -> str:
    """Set an alarm at a local time today or tomorrow.

    Use when the user asks to be woken or reminded at a clock time.

    Args:
        ora: time in 24-hour HH:MM format.
        etichetta: optional label for the alarm.
    """
    try:
        hour, minute = (int(part) for part in ora.strip().split(":", 1))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError as exc:
        raise ToolError("Use a time in HH:MM format, for example 07:30.") from exc

    now = datetime.now().astimezone()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    get_context().db.add_timer(
        etichetta.strip() or "alarm",
        target.astimezone(UTC).isoformat(timespec="seconds"),
    )
    return f"Alarm set for {target.strftime('%H:%M')}."
