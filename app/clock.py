"""The single source of "now". Never call datetime.now() or date.today() elsewhere.

Code that needs the time receives a Clock (FastAPI: Depends(get_clock)),
so tests can replace it with a fixed one.
"""

from datetime import date, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now().astimezone()


def today(clock: Clock) -> date:
    return clock.now().date()


def app_day(moment: datetime, day_starts_at: str) -> date:
    """The app's day: it starts at day_starts_at ("04:00"), so 00:30 may still be yesterday."""
    hours, minutes = map(int, day_starts_at.split(":"))
    return (moment - timedelta(hours=hours, minutes=minutes)).date()
