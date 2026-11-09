from __future__ import annotations

from datetime import UTC, datetime

import pytest
from backend.integrations import calendar_ics
from backend.tools.registry import ToolError

URL = "https://calendar.google.com/calendar/ical/example/basic.ics"

SAMPLE = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Veyra tests//EN
CALSCALE:GREGORIAN
BEGIN:VEVENT
UID:weekly-example-invalid
DTSTAMP:20261101T000000Z
DTSTART:20261109T100000Z
DTEND:20261109T110000Z
SUMMARY:Weekly sync
RRULE:FREQ=WEEKLY;COUNT=3
EXDATE:20261123T100000Z
END:VEVENT
BEGIN:VEVENT
UID:weekly-example-invalid
DTSTAMP:20261101T000000Z
RECURRENCE-ID:20261116T100000Z
DTSTART:20261116T120000Z
DTEND:20261116T130000Z
SUMMARY:Moved sync
END:VEVENT
BEGIN:VEVENT
UID:allday-example-invalid
DTSTAMP:20261101T000000Z
DTSTART;VALUE=DATE:20261110
DTEND;VALUE=DATE:20261112
SUMMARY:Conference
END:VEVENT
END:VCALENDAR
"""

ALL_DAY_RECURRING = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Veyra tests//EN
BEGIN:VEVENT
UID:weekly-allday-example-invalid
DTSTAMP:20261101T000000Z
DTSTART;VALUE=DATE:20261109
DTEND;VALUE=DATE:20261110
SUMMARY:Weekly all day
RRULE:FREQ=WEEKLY;UNTIL=20261116
END:VEVENT
END:VCALENDAR
"""


class _RedirectResponse:
    status_code = 302
    headers: dict[str, str] = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_bytes(self):
        return iter(())


class _RedirectClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def stream(self, method, url):
        return _RedirectResponse()


def test_validate_url_accepts_https_and_rejects_unsafe_addresses():
    assert calendar_ics.validate_url(f"  {URL}\n") == URL

    credentialed = (
        "https://" + "user" + ":" + "pass" + "@calendar.google.com/calendar/ical/example/basic.ics"
    )
    for value in (
        "http://calendar.google.com/calendar/ical/example/basic.ics",
        credentialed,
        "https://calendar.google.com/calendar/ical/example/basic.ics#fragment",
        "not a url",
    ):
        with pytest.raises(ValueError):
            calendar_ics.validate_url(value)


def test_events_are_parsed_with_recurrence_exceptions_and_all_day(monkeypatch):
    monkeypatch.setattr(calendar_ics, "get_secret", lambda name: URL)
    monkeypatch.setattr(calendar_ics, "_download", lambda url: SAMPLE)
    output = calendar_ics.events_between(
        datetime(2026, 11, 9, tzinfo=UTC),
        datetime(2026, 11, 17, tzinfo=UTC),
    )

    assert "<dati_esterni fonte='calendar'>" in output
    assert "Weekly sync" in output
    assert output.count("Moved sync") == 1
    assert "Conference" in output
    assert "2026-11-16" in output
    assert "2026-11-23" not in output


def test_all_day_recurrence_with_date_until(monkeypatch):
    monkeypatch.setattr(calendar_ics, "get_secret", lambda name: URL)
    monkeypatch.setattr(calendar_ics, "_download", lambda url: ALL_DAY_RECURRING)
    output = calendar_ics.events_between(
        datetime(2026, 11, 9, tzinfo=UTC),
        datetime(2026, 11, 17, tzinfo=UTC),
    )

    assert output.count("Weekly all day") == 2
    assert "2026-11-09" in output
    assert "2026-11-16" in output


def test_empty_calendar_returns_the_requested_message(monkeypatch):
    monkeypatch.setattr(calendar_ics, "get_secret", lambda name: URL)
    monkeypatch.setattr(calendar_ics, "_download", lambda url: SAMPLE)
    output = calendar_ics.events_between(
        datetime(2027, 1, 1, tzinfo=UTC),
        datetime(2027, 1, 2, tzinfo=UTC),
    )
    assert output == "No events in that period."


def test_missing_calendar_url_is_reported(monkeypatch):
    monkeypatch.setattr(calendar_ics, "get_secret", lambda name: None)
    with pytest.raises(ToolError, match="not configured"):
        calendar_ics.events_between(
            datetime(2026, 11, 9, tzinfo=UTC),
            datetime(2026, 11, 10, tzinfo=UTC),
        )


def test_redirects_are_rejected(monkeypatch):
    monkeypatch.setattr(calendar_ics.httpx, "Client", lambda **kwargs: _RedirectClient())
    with pytest.raises(ToolError, match="redirects"):
        calendar_ics._download(URL)


def test_calendar_tools_prefer_the_ics_feed(monkeypatch):
    from backend.tools.builtin import google

    monkeypatch.setattr(google.calendar_ics, "configured", lambda: True)
    monkeypatch.setattr(google.calendar_ics, "today_events", lambda: "today-from-ics")
    monkeypatch.setattr(
        google.calendar_ics,
        "events_between",
        lambda start, end: f"{start.date()}..{end.date()}",
    )

    assert google.eventi_oggi() == "today-from-ics"
    assert google.eventi_range("2026-11-09", "2026-11-10") == "2026-11-09..2026-11-10"


def test_calendar_writes_still_require_oauth(monkeypatch):
    from backend.tools.builtin import google

    monkeypatch.setattr(google.calendar_ics, "configured", lambda: True)
    monkeypatch.setattr(google, "get_secret", lambda name: None)
    with pytest.raises(ToolError, match="read-only"):
        google.crea_evento(
            "Planning",
            "2026-11-10T10:00:00",
            "2026-11-10T11:00:00",
        )
