"""Routines: which one is going on now, and what happened to it today.

The server says which routine is on and where it is (by the household's
clock, not the tablet's); the screen (static/js/routine/) ticks the clock,
speaks and counts down on its own between checks. A routine rings from its
wake-up time until its goal, on its days, unless it was finished today.
"""

from dataclasses import dataclass
from datetime import date

from app.children.repository import Child, ChildrenRepository
from app.clock import Clock, app_day
from app.errors import ConflictError, NotFoundError
from app.events.service import EventLog
from app.missions.repository import WEEKDAYS
from app.routines.repository import Part, Routine, RoutinesRepository, RunsRepository, minute_of
from app.settings import SettingsRepository
from app.today.service import DONE, DayService

NOTES = ("started", "stopped", "part", "goal", "closed")


def kids_of(routine: Routine, children: list[Child]) -> list[Child]:
    """The routine's children, in the family's order (none listed: every child)."""
    return [c for c in children if not routine.kids or c.id in routine.kids]


@dataclass
class Person:
    child: Child
    mission: dict | None  # {"id", "name", "done", "total", "completed"}; None: no such mission today


@dataclass
class Current:
    routine: Routine
    day: date
    minute: float  # minute of the day now, with seconds
    run: dict  # see RunsRepository
    people: list[Person]
    warn_minutes: int

    def warnings(self, part: Part) -> list[int]:
        """When the voice warns before the part ends: its own, or else the default
        (only in parts longer than 2 minutes: the 10-second countdown is enough there)."""
        if part.warnings is not None:
            return list(part.warnings)
        return [self.warn_minutes] if self.warn_minutes and part.minutes > 2 else []


class RoutinesService:
    def __init__(
        self,
        routines: RoutinesRepository,
        runs: RunsRepository,
        children: ChildrenRepository,
        days: DayService,
        settings: SettingsRepository,
        clock: Clock,
        events: EventLog,
    ):
        self._routines = routines
        self._runs = runs
        self._children = children
        self._days = days
        self._settings = settings
        self._clock = clock
        self._events = events

    def current(self) -> Current | None:
        """The routine going on at this moment, if any (finished ones stay away today)."""
        settings = self._settings.settings()
        now = self._clock.now()
        day = app_day(now, settings.day_starts_at)
        minute = now.hour * 60 + now.minute + now.second / 60
        for routine in self._routines.list():
            if WEEKDAYS[day.weekday()] not in routine.days or routine.wake is None:
                continue
            if not minute_of(routine.wake) <= minute < routine.ends:
                continue
            run = self._runs.get(day, routine.id)
            if run["finished_at"]:
                continue
            return Current(routine, day, minute, run, self.people(routine), settings.routine_warn_minutes)
        return None

    def current_for(self, routine: Routine, now) -> Current:
        """Any routine as if it were going on at `now` ("Probar ahora")."""
        settings = self._settings.settings()
        minute = now.hour * 60 + now.minute + now.second / 60
        run = {name: None for name in RunsRepository.FIELDS}
        return Current(routine, app_day(now, settings.day_starts_at), minute, run, self.people(routine),
                       settings.routine_warn_minutes)

    def note(self, routine_id: str, kind: str, *, part: int | None = None, seconds: int | None = None,
             early: bool = False, phase: str | None = None) -> None:
        """What the screen tells: it rang, someone stopped it, a part or the goal came, it was closed."""
        current = self._current(routine_id)
        routine, day, run = current.routine, current.day, current.run
        now = self._clock.now()
        if kind == "started":
            if not run["started_at"]:  # once a day, even if the tablet reloads
                self._runs.set(day, routine.id, started_at=now)
                self._events.routine_did("routine_started", routine.name)
        elif kind == "stopped":
            if not run["stopped_at"]:
                self._runs.set(day, routine.id, stopped_at=now)
                self._events.routine_did("routine_stopped", routine.name, seconds=seconds)
        elif kind == "part":
            if part is None or not 0 <= part < len(routine.parts):
                raise NotFoundError("Part not found")
            self._events.routine_did("routine_part", routine.name, part=routine.parts[part].name)
        elif kind == "goal":
            self._events.routine_did("routine_goal", routine.name, early=early)
        elif kind == "closed":
            self._runs.set(day, routine.id, closed_phase=phase)
            self._events.routine_did("routine_closed", routine.name)

    def finish(self, routine_id: str) -> None:
        """Done for today: it does not come back until tomorrow (parents only)."""
        current = self._current(routine_id)
        self._runs.set(current.day, routine_id, finished_at=self._clock.now())
        self._events.routine_did("routine_finished", current.routine.name)

    def _current(self, routine_id: str) -> Current:
        current = self.current()
        if current is None or current.routine.id != routine_id:
            raise ConflictError("That routine is not going on now")
        return current

    def people(self, routine: Routine) -> list[Person]:
        """The routine's children, each with their mission of the routine today."""
        people = []
        for child in kids_of(routine, self._children.list()):
            today = self._days.today(child.id)
            mission_id = routine.missions.get(child.id)
            item = next((m for m in today.missions if m.mission.id == mission_id), None)
            mission = None
            if item:
                total = len(item.mission.steps)
                done = total if item.state == DONE else len(item.checked)
                mission = {"id": item.mission.id, "name": item.mission.name, "done": done, "total": total,
                           "completed": item.state == DONE}
            people.append(Person(child, mission))
        return people
