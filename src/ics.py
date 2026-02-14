from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import uuid

JST = ZoneInfo("Asia/Tokyo")

def to_utc_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%Y%m%dT%H%M%SZ")

def make_ics(title: str, location: str, start: datetime, end: datetime, uid: str | None = None) -> str:
    uid = uid or f"{uuid.uuid4()}@discord-memo-calendar-bot"
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    ics = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "PRODID:-//DiscordMemoCalendarBot//JP//EN\n"
        "CALSCALE:GREGORIAN\n"
        "METHOD:PUBLISH\n"
        "BEGIN:VEVENT\n"
        f"UID:{uid}\n"
        f"DTSTAMP:{dtstamp}\n"
        f"DTSTART:{to_utc_z(start)}\n"
        f"DTEND:{to_utc_z(end)}\n"
        f"SUMMARY:{title}\n"
        f"LOCATION:{location}\n"
        "END:VEVENT\n"
        "END:VCALENDAR\n"
    )
    return ics