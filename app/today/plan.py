"""Which missions a child has on each day of the week: what the day, the streak and the
week of fuel tanks all count from (today's configuration; missions changed later are
not remembered)."""

from collections.abc import Callable
from datetime import date

from app.missions.repository import WEEKDAYS, Mission, child_tasks


def missions_by_day(
    missions: list[Mission], child_id: str, offs: dict[str, dict[str, str]] | None = None
) -> Callable[[date], set[str]]:
    """had(day): the ids of the missions the child has that day (something of theirs to do),
    without the ones a parent let off that day (day_off/: offs by day, as by_day() gives
    them). A whole day off is not taken out here: the week shows it as a free tank."""
    by_weekday = {wd: {m.id for m in missions if child_tasks(m, child_id, wd)} for wd in WEEKDAYS}
    offs = offs or {}
    return lambda day: by_weekday[WEEKDAYS[day.weekday()]] - set(offs.get(day.isoformat(), {}))


def whole_days_off(offs: dict[str, dict[str, str]]) -> set[str]:
    """The days let off whole ("2026-11-19")."""
    return {day for day, off in offs.items() if "" in off}
