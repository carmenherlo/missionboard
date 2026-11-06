"""What a mission's routine means for its hours: two schedules, never one per child.
For a child who follows the routine, on the days it goes, the routine's: from its first
part to its goal (at the latest, when the margin for checking ends); started by hand,
open all day. For everyone else, and on the other days, the mission's.
"""

from app.children.repository import Child
from app.missions.repository import Mission, Schedule
from app.routines.repository import Routine, hhmm


def kids_of(routine: Routine, children: list[Child]) -> list[Child]:
    """The routine's children, in the family's order (none listed: every child)."""
    return [c for c in children if not routine.kids or c.id in routine.kids]


def follows(routine: Routine, child_id: str) -> bool:
    return not routine.kids or child_id in routine.kids


def routine_by_mission(routines: list[Routine]) -> dict[str, Routine]:
    return {routine.mission_id: routine for routine in routines}


def schedule_on(mission: Mission, routine: Routine | None, child_id: str, weekday: str) -> Schedule | None:
    """A child's hours for a mission that day. None: open all day."""
    if routine is None or not follows(routine, child_id) or not routine.goes_on(weekday):
        return mission.schedule
    today = routine.on(weekday)
    if today.manual:
        return None
    return Schedule(start=hhmm(today.starts), end=hhmm(today.ends))
