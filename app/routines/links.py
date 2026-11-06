"""Which routine each mission goes with: a mission chosen for a child in a routine
follows the routine's hours on the routine's days; its own hours count on the others.

- A routine that rings at a time: the mission opens when its first part starts and
  closes at its goal (at the latest, when the margin for checking ends).
- One started by hand: open all day, on the routine's days.
- In two routines (one on weekdays, one at the weekend): each day, the routines of
  that day; two on the same day, from the first one's start to the last one's end.
"""

from app.children.repository import Child
from app.missions.repository import Mission, Schedule
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


def schedule_on(mission: Mission, routines: list[Routine], children: list[Child], child_id: str,
                weekday: str) -> Schedule | None:
    """A child's hours for a mission that day: the routine's, if they follow it and it
    goes that day; else the mission's. None: open all day."""
    kids = {c.id: c for c in children}
    today = [r.on(weekday) for r in routines
             if weekday in r.days and r.missions.get(child_id) == mission.id
             and child_id in kids and kids[child_id] in kids_of(r, children)]
    if not today:
        return mission.schedule
    if any(r.manual for r in today):
        return None
    return Schedule(start=hhmm(min(r.starts for r in today)), end=hhmm(max(r.ends for r in today)))
