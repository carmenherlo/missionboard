"""The single source of "now". Never call datetime.now() or date.today() elsewhere.

Code that needs the time receives a Clock (FastAPI: Depends(get_clock)),
so tests can replace it with a fixed one.
"""

from datetime import date, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now().astimezone()


def today(clock: Clock) -> date:
    return clock.now().date()


def app_day(moment: datetime) -> date:
    """The app's day: the calendar day, from 00:00 (its own start time went, 27/11)."""
    return moment.date()
