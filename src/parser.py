import re
from dataclasses import dataclass
from datetime import datetime

PATTERN_TIME = re.compile(r"(\d+)/(\d+)\s+(.+?)\s+(\d+):(\d+)-(\d+):(\d+)")
PATTERN_DAY  = re.compile(r"(\d+)/(\d+)\s+(.+)$")  # 時間なし

@dataclass
class EventDraft:
    title: str
    location: str
    start: datetime
    end: datetime
    all_day: bool = False

def guess_year(month: int, now: datetime) -> int:
    return now.year + 1 if month < now.month else now.year

def parse_event_line(line: str, now: datetime | None = None) -> EventDraft | None:
    now = now or datetime.now()

    m = PATTERN_TIME.search(line)
    if m:
        month = int(m.group(1)); day = int(m.group(2))
        raw_title = m.group(3).strip()
        sh, sm, eh, em = int(m.group(4)), int(m.group(5)), int(m.group(6)), int(m.group(7))

        year = guess_year(month, now)
        start = datetime(year, month, day, sh, sm)
        end = datetime(year, month, day, eh, em)

        parts = raw_title.split()
        location = parts[0] if parts else ""
        title = raw_title
        return EventDraft(title=title, location=location, start=start, end=end, all_day=False)

    m = PATTERN_DAY.search(line)
    if m:
        month = int(m.group(1)); day = int(m.group(2))
        raw_title = m.group(3).strip()

        year = guess_year(month, now)
        start = datetime(year, month, day, 0, 0)
        end = datetime(year, month, day, 0, 0)  # 終日はURL生成側で「翌日」にする

        parts = raw_title.split()
        location = parts[0] if parts else ""
        title = raw_title
        return EventDraft(title=title, location=location, start=start, end=end, all_day=True)

    return None

def parse_events(text: str) -> list[EventDraft]:
    events: list[EventDraft] = []
    for line in text.splitlines():
        ev = parse_event_line(line.strip())
        if ev:
            events.append(ev)
    return events