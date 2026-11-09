"""Read-only calendar support through a secret iCalendar feed.

The feed address is a bearer secret: it is stored in the OS credential store
and is never returned by the HTTP API. This module only reads events. Creating
or changing events still uses the Google OAuth client.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, time, timedelta, tzinfo
from typing import Any
from urllib.parse import urlparse

import httpx
from dateutil.rrule import rrulestr
from icalendar import Calendar

from backend.secrets import get_secret
from backend.tools.external import wrap_external
from backend.tools.registry import ToolError

SECRET_NAME = "calendar_ics_url"
MAX_FEED_BYTES = 5 * 1024 * 1024
REQUEST_TIMEOUT_S = 10.0
MAX_SCAN = 2000
_UNTIL_DATE = re.compile(r"UNTIL=(\d{8})(?=;|$)")


def validate_url(value: str) -> str:
    """Validate a secret HTTPS iCalendar feed address and return it stripped."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("The calendar URL is empty.")
    if len(cleaned) > 2048:
        raise ValueError("The calendar URL is too long.")
    if any(character.isspace() for character in cleaned):
        raise ValueError("The calendar URL cannot contain whitespace.")
    try:
        parsed = urlparse(cleaned)
    except ValueError as exc:
        raise ValueError("The calendar URL is invalid.") from exc
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("The calendar URL must be an https URL.")
    if parsed.username or parsed.password:
        raise ValueError("The calendar URL cannot contain credentials.")
    if parsed.fragment:
        raise ValueError("The calendar URL cannot contain a fragment.")
    return cleaned


def configured() -> bool:
    """Return True when a secret calendar feed address is available."""
    return bool(get_secret(SECRET_NAME))


def _feed_url() -> str:
    value = get_secret(SECRET_NAME)
    if not value:
        raise ToolError("Calendar is not configured. Add a secret iCal URL in Settings > Accounts.")
    try:
        return validate_url(value)
    except ValueError as exc:
        raise ToolError(f"The calendar URL is invalid: {exc}") from exc


def _download(url: str) -> bytes:
    headers = {
        "Accept": "text/calendar, text/plain;q=0.9, */*;q=0.1",
        "User-Agent": "Veyra calendar reader",
    }
    try:
        with (
            httpx.Client(
                timeout=httpx.Timeout(REQUEST_TIMEOUT_S),
                follow_redirects=False,
                headers=headers,
            ) as client,
            client.stream("GET", url) as response,
        ):
            if response.status_code in {301, 302, 303, 307, 308}:
                raise ToolError(
                    "The calendar URL redirects. Use the final secret iCal address "
                    "from Google Calendar."
                )
            if response.status_code != 200:
                raise ToolError(f"The calendar feed returned HTTP {response.status_code}.")
            content_type = response.headers.get("content-type", "").lower()
            if content_type.startswith("text/html"):
                raise ToolError("The calendar URL returned a web page, not an iCalendar feed.")

            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > MAX_FEED_BYTES:
                    raise ToolError("The calendar feed is too large.")
                chunks.append(chunk)
            return b"".join(chunks)
    except ToolError:
        raise
    except httpx.TimeoutException as exc:
        raise ToolError("The calendar feed timed out.") from exc
    except httpx.HTTPError as exc:
        raise ToolError(
            "Could not download the calendar feed. Check the URL and the network connection."
        ) from exc


def _parse_feed(data: bytes) -> Calendar:
    try:
        calendar = Calendar.from_ical(data)
    except Exception as exc:
        raise ToolError("The calendar feed is not valid iCalendar data.") from exc
    if not isinstance(calendar, Calendar):
        raise ToolError("The calendar feed is not valid iCalendar data.")
    return calendar


def _as_datetime(value: date | datetime, zone: tzinfo) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=zone)
    return datetime.combine(value, time.min, tzinfo=zone)


def _property_dt(event: Any, name: str) -> Any:
    prop = event.get(name)
    return getattr(prop, "dt", None) if prop is not None else None


def _property_dts(event: Any, name: str) -> list[Any]:
    prop = event.get(name)
    if prop is None:
        return []
    props = prop if isinstance(prop, list) else [prop]
    values: list[Any] = []
    for item in props:
        dts = getattr(item, "dts", None)
        if dts:
            values.extend(getattr(entry, "dt", None) for entry in dts)
        else:
            value = getattr(item, "dt", None)
            if value is not None:
                values.append(value)
    return [value for value in values if value is not None]


def _summary(event: Any) -> str:
    value = event.get("SUMMARY")
    text = " ".join(str(value).split()) if value is not None else ""
    return text or "(no title)"


def _duration(event: Any, start: date | datetime) -> timedelta:
    end = _property_dt(event, "DTEND")
    if isinstance(start, datetime):
        if isinstance(end, datetime):
            if start.tzinfo is None and end.tzinfo is not None:
                start = start.replace(tzinfo=end.tzinfo)
            elif start.tzinfo is not None and end.tzinfo is None:
                end = end.replace(tzinfo=start.tzinfo)
            delta = end - start
            if delta > timedelta(0):
                return delta
        elif isinstance(end, date):
            end_dt = datetime.combine(end, time.min, tzinfo=start.tzinfo)
            delta = end_dt - start
            if delta > timedelta(0):
                return delta
    elif isinstance(end, date):
        delta = datetime.combine(end, time.min) - datetime.combine(start, time.min)
        if delta > timedelta(0):
            return delta

    raw_duration = _property_dt(event, "DURATION")
    if isinstance(raw_duration, timedelta) and raw_duration > timedelta(0):
        return raw_duration
    return timedelta(days=1) if not isinstance(start, datetime) else timedelta(0)


def _moment_key(value: date | datetime, zone: tzinfo) -> datetime:
    return _as_datetime(value, zone).astimezone(UTC)


def _overlaps(
    start: date | datetime,
    end: date | datetime,
    window_start: datetime,
    window_end: datetime,
    zone: tzinfo,
) -> bool:
    start_dt = _as_datetime(start, zone)
    end_dt = _as_datetime(end, zone)
    if end_dt <= start_dt:
        return window_start <= start_dt < window_end
    return start_dt < window_end and end_dt > window_start


def _rule_text(event: Any) -> str:
    rule = event.get("RRULE")
    if isinstance(rule, list):
        rule = rule[0]
    text = rule.to_ical().decode("utf-8")
    # RFC 5545 requires an all-day UNTIL to be a DATE. dateutil needs a UTC
    # datetime when DTSTART carries a timezone, so normalize it to end of day.
    return _UNTIL_DATE.sub(lambda match: f"UNTIL={match.group(1)}T235959Z", text)


def _single_event(
    event: Any,
    window_start: datetime,
    window_end: datetime,
    zone: tzinfo,
) -> list[tuple[date | datetime, str]]:
    start = _property_dt(event, "DTSTART")
    if not isinstance(start, (date, datetime)):
        return []
    end = start + _duration(event, start)
    if not _overlaps(start, end, window_start, window_end, zone):
        return []
    return [(start, _summary(event))]


def _expand_event(
    event: Any,
    window_start: datetime,
    window_end: datetime,
    zone: tzinfo,
    overrides: dict[str, set[datetime]],
) -> list[tuple[date | datetime, str]]:
    start = _property_dt(event, "DTSTART")
    if not isinstance(start, (date, datetime)):
        return []

    duration = _duration(event, start)
    start_dt = _as_datetime(start, zone)
    scan_start = window_start - duration
    exdates = {_moment_key(value, zone) for value in _property_dts(event, "EXDATE")}
    uid = str(event.get("UID", ""))
    overridden = overrides.get(uid, set())
    found: list[tuple[date | datetime, str]] = []
    all_day = not isinstance(start, datetime)

    rule = event.get("RRULE")
    if rule:
        try:
            recurring = rrulestr(_rule_text(event), dtstart=start_dt)
            occurrences = recurring.between(scan_start, window_end, inc=True)
        except (TypeError, ValueError):
            occurrences = [start_dt]
    else:
        occurrences = [start_dt]

    for occurrence in occurrences[:MAX_SCAN]:
        value: date | datetime = occurrence.date() if all_day else occurrence
        key = _moment_key(value, zone)
        if key in exdates or key in overridden:
            continue
        end = value + duration
        if _overlaps(value, end, window_start, window_end, zone):
            found.append((value, _summary(event)))

    for extra in _property_dts(event, "RDATE"):
        value = extra.date() if all_day and isinstance(extra, datetime) else extra
        if not isinstance(value, (date, datetime)):
            continue
        key = _moment_key(value, zone)
        if key in exdates or key in overridden:
            continue
        end = value + duration
        if _overlaps(value, end, window_start, window_end, zone):
            found.append((value, _summary(event)))
    return found


def _collect_events(
    calendar: Calendar,
    window_start: datetime,
    window_end: datetime,
    zone: tzinfo,
    limit: int,
) -> list[tuple[date | datetime, str]]:
    events = calendar.walk("VEVENT")
    overrides: dict[str, set[datetime]] = {}
    for event in events:
        recurrence_id = _property_dt(event, "RECURRENCE-ID")
        uid = str(event.get("UID", ""))
        if recurrence_id is not None and uid:
            overrides.setdefault(uid, set()).add(_moment_key(recurrence_id, zone))

    found: list[tuple[date | datetime, str]] = []
    for event in events:
        if _property_dt(event, "RECURRENCE-ID") is not None:
            found.extend(_single_event(event, window_start, window_end, zone))
        elif event.get("RRULE") or _property_dts(event, "RDATE"):
            found.extend(_expand_event(event, window_start, window_end, zone, overrides))
        else:
            found.extend(_single_event(event, window_start, window_end, zone))
        if len(found) >= MAX_SCAN:
            break

    found.sort(key=lambda item: _as_datetime(item[0], zone))
    unique: list[tuple[date | datetime, str]] = []
    seen: set[tuple[datetime, str]] = set()
    for start, title in found:
        key = (_moment_key(start, zone), title)
        if key in seen:
            continue
        seen.add(key)
        unique.append((start, title))
        if len(unique) >= limit:
            break
    return unique


def _format_start(value: date | datetime, zone: tzinfo) -> str:
    if isinstance(value, datetime):
        moment = value if value.tzinfo is not None else value.replace(tzinfo=zone)
        return moment.astimezone(zone).strftime("%Y-%m-%d %H:%M")
    return value.isoformat()


def events_between(
    start: datetime,
    end: datetime,
    *,
    empty: str = "No events in that period.",
    limit: int = 50,
) -> str:
    """Return formatted events from the secret iCal feed between two moments."""
    zone = datetime.now().astimezone().tzinfo
    if zone is None:
        raise ToolError("The local timezone is unavailable.")
    window_start = _as_datetime(start, zone)
    window_end = _as_datetime(end, zone)
    if window_end <= window_start:
        raise ToolError("The end must be after the start.")

    calendar = _parse_feed(_download(_feed_url()))
    events = _collect_events(calendar, window_start, window_end, zone, limit)
    if not events:
        return empty
    lines = [f"{_format_start(value, zone)} | {title}" for value, title in events]
    return wrap_external("calendar", "\n".join(lines))


def today_events() -> str:
    """Return today's events from the secret iCal feed."""
    now = datetime.now().astimezone()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return events_between(
        start,
        start + timedelta(days=1),
        empty="No events today.",
        limit=20,
    )
