"""Routines: which one is going on now, and what happened to it today.

The server says which routine is on and where it is (by the household's
clock, not the tablet's); the screen (static/js/routine/) ticks the clock,
speaks and counts down on its own between checks. A routine rings from its
wake-up time until its goal, on its days, unless it was finished today.
"""

import json
from dataclasses import dataclass
from datetime import date, datetime

from app.children.repository import Child, ChildrenRepository
from app.clock import Clock, app_day
from app.errors import ConflictError, InvalidError, NotFoundError
from app.events.service import EventLog
from app.missions.repository import WEEKDAYS
from app.routines.repository import Part, Routine, RoutinesRepository, RunsRepository, minute_of
from app.settings import SettingsRepository
from app.today.service import DONE, DayService

NOTES = ("started", "stopped", "part", "goal", "closed", "ended")


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
    started: float | None = None  # started by hand: the minute of the day it started, with seconds

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
        """The routine going on at this moment, if any: one started by hand (until its
        time is up), or else one ringing by its time (finished ones stay away today)."""
        settings = self._settings.settings()
        now = self._clock.now()
        day = app_day(now, settings.day_starts_at)
        minute = now.hour * 60 + now.minute + now.second / 60
        weekday = WEEKDAYS[day.weekday()]
        for stored in self._routines.list():
            run = self._runs.get(day, stored.id) if stored.manual else None
            if not run or not run["started_at"]:
                continue
            started = datetime.fromisoformat(run["started_at"])
            start = started.hour * 60 + started.minute + started.second / 60
            if minute < start + stored.length:
                kids = json.loads(run["kids"] or "[]")
                people = [p for p in self.people(stored) if p.child.id in kids]
                return Current(stored.started_at(int(start)), day, minute, run, people,
                               settings.routine_warn_minutes, started=start)
        for stored in self._routines.list():
            if weekday not in stored.days or stored.manual:
                continue
            routine = stored.on(weekday)
            if not minute_of(routine.wake) <= minute < routine.ends:
                continue
            run = self._runs.get(day, routine.id)
            if run["finished_at"]:
                continue
            return Current(routine, day, minute, run, self.people(routine), settings.routine_warn_minutes)
        return None

    def current_for(self, routine: Routine, now) -> Current:
        """Any routine as if it were going on at `now` ("Probar ahora"); one started by
        hand, as if started now with all its children."""
        settings = self._settings.settings()
        minute = now.hour * 60 + now.minute + now.second / 60
        run = {name: None for name in RunsRepository.FIELDS}
        started = None
        if routine.manual:
            started, routine = minute, routine.started_at(int(minute))
        return Current(routine, app_day(now, settings.day_starts_at), minute, run, self.people(routine),
                       settings.routine_warn_minutes, started=started)

    def by_hand(self) -> list[tuple[Routine, list[Child]]]:
        """The routines that can be started by hand today, each with its children."""
        settings = self._settings.settings()
        weekday = WEEKDAYS[app_day(self._clock.now(), settings.day_starts_at).weekday()]
        children = self._children.list()
        return [(r, kids_of(r, children)) for r in self._routines.list() if r.manual and weekday in r.days]

    def start(self, routine_id: str, kids: list[str]) -> None:
        """Start a routine by hand with the children who have come home."""
        found = next(((r, c) for r, c in self.by_hand() if r.id == routine_id), None)
        if found is None:
            raise NotFoundError("No routine to start by hand today with that id")
        routine, children = found
        if not kids or any(k not in {c.id for c in children} for k in kids):
            raise InvalidError("Choose who has come home, among the routine's children")
        now = self._clock.now()
        day = app_day(now, self._settings.settings().day_starts_at)
        self._runs.clear(day, routine_id)
        self._runs.set(day, routine_id, started_at=now, kids=json.dumps(kids))
        self._events.routine_did("routine_started", routine.name)

    def note(self, routine_id: str, kind: str, *, part: int | None = None, seconds: int | None = None,
             early: bool = False, phase: str | None = None) -> None:
        """What the screen tells: it rang, someone stopped it, a part or the goal came, it was
        closed, or (started by hand) it ended: its time is up then, so it is no longer on."""
        if kind == "ended":
            routine = next((r for r in self._routines.list() if r.id == routine_id), None)
            if routine is None:
                raise NotFoundError("Routine not found")
            self._runs.clear(app_day(self._clock.now(), self._settings.settings().day_starts_at), routine_id)
            self._events.routine_did("routine_ended", routine.name, early=early)
            return
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
