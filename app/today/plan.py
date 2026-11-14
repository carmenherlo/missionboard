"""Which missions a child has on each day of the week: what the day, the streak and the
week of fuel tanks all count from (today's configuration; missions changed later are
not remembered)."""

from collections.abc import Callable
from datetime import date

from app.missions.repository import WEEKDAYS, Mission, child_tasks


def missions_by_day(missions: list[Mission], child_id: str) -> Callable[[date], set[str]]:
    """had(day): the ids of the missions the child has that day (something of theirs to do)."""
    by_weekday = {wd: {m.id for m in missions if child_tasks(m, child_id, wd)} for wd in WEEKDAYS}
    return lambda day: by_weekday[WEEKDAYS[day.weekday()]]
