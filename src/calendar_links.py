from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, quote


def _to_utc(dt: datetime) -> datetime:
    """
    naive datetime を JST とみなして UTC に変換。
    既に tz-aware の場合はそのまま UTC に変換。
    """
    if dt.tzinfo is None:
        jst = timezone(timedelta(hours=9))
        dt = dt.replace(tzinfo=jst)
    return dt.astimezone(timezone.utc)


def google_template_url(
    title: str,
    start: datetime,
    end: datetime,
    *,
    all_day: bool = False,
    details: str = "",
) -> str:
    """
    Googleカレンダーの template URL を返す。
    - all_day=True: dates=YYYYMMDD/YYYYMMDD(翌日)
    - all_day=False: dates=YYYYMMDDTHHMMSSZ/YYYYMMDDTHHMMSSZ (UTC)
    """
    base = "https://calendar.google.com/calendar/render"
    params: dict[str, str] = {"action": "TEMPLATE", "text": title}

    if details:
        params["details"] = details

    if all_day:
        s = start.strftime("%Y%m%d")
        # 終日は「翌日」を end にするのがGoogleの作法
        end_next = (start + timedelta(days=1)).strftime("%Y%m%d")
        params["dates"] = f"{s}/{end_next}"
    else:
        s_utc = _to_utc(start).strftime("%Y%m%dT%H%M%SZ")
        e_utc = _to_utc(end).strftime("%Y%m%dT%H%M%SZ")
        params["dates"] = f"{s_utc}/{e_utc}"

    return f"{base}?{urlencode(params, quote_via=quote)}"