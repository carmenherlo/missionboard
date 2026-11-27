"""A routine with a time and its mission's hours (rutina-en-mision.html, 27/11): the routine
must fit in them, so a change to the routine that leaves them opens them, saved with it,
and says so in the log. They never close in by themselves: narrowing the mission past its
routine is refused (missions/service.py)."""

from app.events.service import EventLog
from app.missions.repository import Mission, MissionsRepository, Schedule
from app.routines.links import DAY_END, fits
from app.routines.model import Routine
from app.routines.timing import hhmm, minute_of


def widened(routine: Routine, mission: Mission) -> Schedule | None:
    """The mission's hours, opened enough for its routine to fit (rutina-en-mision.html):
    None if it already fits. They never close in by themselves."""
    if routine.off or fits(routine, mission):
        return None
    days = [routine.on(day) for day in routine.days if routine.goes_on(day)]
    start = min(minute_of(mission.schedule.start), *(r.starts for r in days))
    end = mission.schedule.end and hhmm(min(DAY_END - 1, max(minute_of(mission.schedule.end), *(r.ends for r in days))))
    return Schedule(start=hhmm(start), end=end)


def open_for(routine: Routine, missions: MissionsRepository, events: EventLog) -> None:
    """Open the mission's hours if its routine no longer fits in them."""
    mission = missions.get(routine.mission_id)
    if schedule := widened(routine, mission):
        mission.schedule = schedule
        missions.update(mission)
        events.config_changed("mission", "changed", mission=mission, changes={"schedule": schedule})
