import re
from dataclasses import dataclass
from datetime import datetime
print("PARSER_VERSION=9964ba5")

# 例: 2/27 なんとか 13:45-15:25
# 例: 2/27 なんとか『タイトル』13:45-15:25（スペース無しでもOK）
PATTERN_TIME = re.compile(
    r"(\d+)/(\d+)\s+(.+?)\s*(\d{1,2}):(\d{2})\s*[-–—〜~]\s*(\d{1,2}):(\d{2})"
)

# 例: 2/25 夜ご飯（時間なし → 終日）
PATTERN_DAY = re.compile(r"(\d+)/(\d+)\s+(.+)$")

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

    # 1) 時間レンジがあるなら「時間つき」
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

    # 2) 時間が無いなら「終日」
    m = PATTERN_DAY.search(line)
    if m:
        month = int(m.group(1)); day = int(m.group(2))
        raw_title = m.group(3).strip()

        year = guess_year(month, now)
        start = datetime(year, month, day, 0, 0)
        end = datetime(year, month, day, 0, 0)  # 終日はリンク生成側で翌日にする

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