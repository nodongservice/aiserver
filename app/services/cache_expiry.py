from datetime import datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

SEOUL_TZ = ZoneInfo("Asia/Seoul")
DAILY_CACHE_EXPIRY_HOUR = 2


def get_next_daily_cache_expiry_at(now: Optional[datetime] = None) -> datetime:
    base = now.astimezone(SEOUL_TZ) if now else datetime.now(SEOUL_TZ)
    candidate = datetime.combine(base.date(), time(hour=DAILY_CACHE_EXPIRY_HOUR), tzinfo=SEOUL_TZ)

    if base >= candidate:
        candidate += timedelta(days=1)

    return candidate
