from urllib.parse import urlencode, quote
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

def to_utc_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%Y%m%dT%H%M%SZ")

def to_yyyymmdd(dt: datetime) -> str:
    # 終日用（日付だけ）
    return dt.strftime("%Y%m%d")

def google_template_url(title: str, location: str, start: datetime, end: datetime, all_day: bool = False) -> str:
    if all_day:
        # 終日: endは翌日（排他的）
        start_d = to_yyyymmdd(start)
        end_d = to_yyyymmdd(start + timedelta(days=1))
        dates = f"{start_d}/{end_d}"
    else:
        dates = f"{to_utc_z(start)}/{to_utc_z(end)}"

    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": dates,
        "location": location or "",
        "details": "From Discord memo",
    }
    return "https://calendar.google.com/calendar/render?" + urlencode(params, quote_via=quote)