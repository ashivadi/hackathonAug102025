from datetime import datetime
from zoneinfo import ZoneInfo

def now_tz(tz_name: str):
    tz = ZoneInfo(tz_name)
    return datetime.now(tz)

def day_bounds(tz_name: str, dt: datetime | None = None):
    tz = ZoneInfo(tz_name)
    now = (dt or datetime.now(tz)).astimezone(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end
