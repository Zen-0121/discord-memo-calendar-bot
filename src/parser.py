import re
from dataclasses import dataclass
from datetime import datetime

# メモ区切り: "｜" または "|"
SPLIT_NOTE_RE = re.compile(r"\s*[｜|]\s*", re.UNICODE)

# 時間あり: 2/27 タイトル 13:45-15:25
# タイトルと時刻の間の空白は「任意」
# ハイフンは複数種類許容
PATTERN_TIME = re.compile(
    r"(\d+)/(\d+)\s+(.+?)\s*(\d{1,2}):(\d{2})\s*[-–—〜~]\s*(\d{1,2}):(\d{2})"
)

# 時間なし: 2/27 タイトル
PATTERN_DAY = re.compile(r"(\d+)/(\d+)\s+(.+)$")


@dataclass
class EventDraft:
    title: str
    start: datetime
    end: datetime
    all_day: bool = False
    notes: str = ""


def guess_year(month: int, now: datetime) -> int:
    return now.year + 1 if month < now.month else now.year


def split_main_and_notes(line: str) -> tuple[str, str]:
    """
    '2/27 タイトル 13:45-15:25｜メモ...' → ('2/27 ... 13:45-15:25', 'メモ...')
    区切りが無ければ notes は空文字。
    """
    parts = SPLIT_NOTE_RE.split(line, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return line.strip(), ""


def parse_event_line(line: str, now: datetime | None = None) -> EventDraft | None:
    now = now or datetime.now()
    if not line:
        return None

    main, notes = split_main_and_notes(line)

    m = PATTERN_TIME.search(main)
    if m:
        month = int(m.group(1))
        day = int(m.group(2))
        raw_title = m.group(3).strip()
        sh, sm = int(m.group(4)), int(m.group(5))
        eh, em = int(m.group(6)), int(m.group(7))

        year = guess_year(month, now)
        start = datetime(year, month, day, sh, sm)
        end = datetime(year, month, day, eh, em)

        return EventDraft(
            title=raw_title,
            start=start,
            end=end,
            all_day=False,
            notes=notes,
        )

    m = PATTERN_DAY.search(main)
    if m:
        month = int(m.group(1))
        day = int(m.group(2))
        raw_title = m.group(3).strip()

        year = guess_year(month, now)
        start = datetime(year, month, day, 0, 0)
        end = datetime(year, month, day, 0, 0)  # 終日はURL生成側で翌日にする

        return EventDraft(
            title=raw_title,
            start=start,
            end=end,
            all_day=True,
            notes=notes,
        )

    return None


def parse_events(text: str) -> list[EventDraft]:
    events: list[EventDraft] = []
    for line in text.splitlines():
        ev = parse_event_line(line.strip())
        if ev:
            events.append(ev)
    return events