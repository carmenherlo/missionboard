"""Which routine each mission goes with (rutinas-8): a mission chosen for a child in
a routine follows the routine's days and hours, not its own. Its own schedule is kept,
unused, for when it leaves the routine.

- A routine that rings at a time: the mission opens when its first part starts and
  closes at its goal (at the latest, when the margin for checking ends).
- One started by hand: open all day, on the routine's days.
- In two routines (one on weekdays, one at the weekend): each day, the routines of
  that day; two on the same day, from the first one's start to the last one's end.
"""

from app.children.repository import Child
from app.missions.repository import WEEKDAYS, Mission, Schedule
from app.routines.repository import Routine, hhmm


def kids_of(routine: Routine, children: list[Child]) -> list[Child]:
    """The routine's children, in the family's order (none listed: every child)."""
    return [c for c in children if not routine.kids or c.id in routine.kids]


def routines_by_mission(routines: list[Routine], children: list[Child]) -> dict[str, list[Routine]]:
    """Each mission's routines: the ones where it is a child's mission (and the child is in it)."""
    found: dict[str, list[Routine]] = {}
    for routine in routines:
        kids = {c.id for c in kids_of(routine, children)}
        for child_id, mission_id in routine.missions.items():
            if mission_id and child_id in kids:
                found.setdefault(mission_id, []).append(routine)
    return found


def days_of(mission: Mission, routines: list[Routine]) -> tuple[str, ...]:
    """Its days: the routines' days if it goes with any, else its own."""
    if not routines:
        return mission.days
    return tuple(sorted({day for r in routines for day in r.days}, key=WEEKDAYS.index))


def schedule_on(mission: Mission, routines: list[Routine], weekday: str) -> Schedule | None:
    """Its hours that day: the routines' (moved days included), else its own. None: open all day."""
    if not routines:
        return mission.schedule
    today = [r.on(weekday) for r in routines if weekday in r.days]
    if not today or any(r.manual for r in today):
        return None
    return Schedule(start=hhmm(min(r.starts for r in today)), end=hhmm(max(r.ends for r in today)))

