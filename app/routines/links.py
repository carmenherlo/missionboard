"""A mission and its routine. The mission's hours rule, for every child and every day:
a routine with a time has to fit inside them (from its alarm to its goal); one started
by hand can start any time, and starting it opens its mission that day (see service.py).
"""

from app.children.repository import Child
from app.errors import ConflictError
from app.missions.repository import Mission
from app.routines.model import Routine
from app.routines.timing import minute_of

DAY_END = 24 * 60
OUTSIDE = "It does not fit in its mission's hours"  # the screens tell it by these words


def kids_of(routine: Routine, children: list[Child]) -> list[Child]:
    """The routine's children, in the family's order (none listed: every child)."""
    return [c for c in children if not routine.kids or c.id in routine.kids]


def routine_by_mission(routines: list[Routine]) -> dict[str, Routine]:
    return {routine.mission_id: routine for routine in routines}


def fits(routine: Routine, mission: Mission) -> bool:
    """On every day it goes, from its alarm to its goal inside its mission's hours."""
    if routine.manual or mission.schedule is None:
        return True
    opens = minute_of(mission.schedule.start)
    closes = minute_of(mission.schedule.end) if mission.schedule.end else DAY_END
    days = [routine.on(day) for day in routine.days if routine.goes_on(day)]
    return all(opens <= minute_of(r.wake) and r.ends <= closes for r in days)


def check_fits(routine: Routine, mission: Mission | None) -> None:
    if mission is not None and not fits(routine, mission):
        raise ConflictError(OUTSIDE)
