"""Routines: which one is going on now, and what happened to it today.

The server says which routine is on and where it is (by the household's
clock, not the tablet's); the screen (static/js/routine/) ticks the clock,
speaks and counts down on its own between checks. A routine rings from its
wake-up time until its goal, on its days, unless it was finished today.
"""

import json
from datetime import date, datetime, time, timedelta

from app.children.repository import Child, ChildrenRepository
from app.clock import Clock, app_day
from app.errors import ConflictError, InvalidError, NotFoundError
from app.events.service import EventLog
from app.missions.repository import WEEKDAYS, MissionsRepository
from app.routines.current import Current
from app.routines.model import Routine
from app.routines.people import People, Person
from app.routines.race_flag import RaceFlag
from app.routines.race_rules import INICIO_SECONDS, RECORD_RACES, START_SECONDS, Pace, pace_of
from app.routines.races_repository import RacesRepository
from app.routines.repository import RoutinesRepository, RunsRepository
from app.routines.timed_memory import as_by_hand
from app.routines.timing import minute_of
from app.routines.who_left import Startable, WhoLeft
from app.today.service import DayService

NOTES = ("started", "stopped", "part", "goal", "closed", "reopened", "ended")


class RoutinesService:
    def __init__(
        self,
        routines: RoutinesRepository,
        runs: RunsRepository,
        children: ChildrenRepository,
        days: DayService,
        clock: Clock,
        events: EventLog,
        missions: MissionsRepository,
        races: RacesRepository,
    ):
        self._races = races
        self._flag = RaceFlag(runs, races, events)
        self._missions = missions
        self._people = People(children, days, missions)
        self._who_left = WhoLeft(children, days, missions, runs, races)
        self._routines = routines
        self._runs = runs
        self._children = children
        self._days = days
        self._clock = clock
        self._events = events

    def _live(self) -> list[Routine]:
        """The routines that ring and start."""
        return self._routines.live()

    def current(self) -> Current | None:
        """The routine going on at this moment, if any: one started by hand (until its
        time is up), or else one ringing by its time (finished ones stay away today)."""
        now = self._clock.now()
        day = app_day(now)
        minute = _minute(now)
        weekday = WEEKDAYS[day.weekday()]
        for stored in self._live():  # started by hand: one that is, or one that rings at a time (who_left.py)
            run = self._runs.get(day, stored.id)
            if not (stored.manual or run["by_hand"]) or not run["started_at"] or run["finished_at"]:
                continue
            stored = stored if stored.manual else as_by_hand(stored)
            start = _minute(datetime.fromisoformat(run["started_at"]))
            moment = datetime.fromisoformat(run["paused_at"]) if run["paused_at"] else now  # paused: still
            at = _minute(moment)
            routine = stored.on(weekday).lengthened(json.loads(run["extra"] or "{}"))  # ± minutes today
            people = self.people(_with_kids(stored, run))
            pace = self.pace(stored)
            if routine.racing:  # until the flag and its landing, or lost (race_flag.py)
                if not self._flag.goes_on(routine, day, run, people, pace, moment):
                    continue
            elif at >= start + routine.length:
                continue
            race = self._flag.today(routine.id, day, run) if routine.racing else {}
            return Current(routine.started_at(int(start)), day, at, run, people, started=start, pace=pace, **race)
        for stored in self._live():
            if not stored.goes_on(weekday) or stored.manual:
                continue
            routine = stored.on(weekday)
            if not minute_of(routine.wake) <= minute < routine.ends:
                continue
            run = self._runs.get(day, routine.id)
            if run["finished_at"] or run["by_hand"] or self._everyone_off(routine):
                continue
            return Current(routine, day, minute, run, self.people(_with_kids(routine, run)))
        return None

    def current_for(self, routine: Routine, now) -> Current:
        """Any routine as if it were going on at `now` ("Probar ahora"); one started by
        hand, as if started now with all its children."""
        minute = now.hour * 60 + now.minute + now.second / 60
        run = dict.fromkeys(RunsRepository.FIELDS)
        started = None
        if routine.manual:
            # As when launched: "Va a empezar la misión…" first (a race counts in by itself, race.js)
            started, routine = minute + (0 if routine.racing else INICIO_SECONDS / 60), routine.started_at(int(minute))
        return Current(
            routine,
            app_day(now),
            minute,
            run,
            self.people(routine, trial=True),
            started=started,
            pace=self.pace(routine),
        )

    def notices(self) -> list[dict]:
        """Today's notices before the routines ring: {"routine", "at" (minute of the day), "say"}."""
        day = app_day(self._clock.now())
        weekday = WEEKDAYS[day.weekday()]
        found = []
        for stored in self._live():
            if stored.manual or not stored.goes_on(weekday) or self._runs.get(day, stored.id)["finished_at"]:
                continue
            routine = stored.on(weekday)
            for notice in routine.notices:
                found.append({"routine": routine.id, "at": minute_of(routine.wake) - notice.minutes, "say": notice.say})
        return found

    def next_ring(self, days_ahead: int = 7) -> tuple[Routine, datetime] | None:
        """The next routine to ring after now (the clock screen): from today on, each
        day as it goes that day (moved days included). Started by hand, never."""
        now = self._clock.now()
        found = None
        for ahead in range(days_ahead + 1):
            date = (now + timedelta(days=ahead)).date()
            weekday = WEEKDAYS[date.weekday()]
            for stored in self._live():
                if stored.manual or not stored.goes_on(weekday):
                    continue
                routine = stored.on(weekday)
                wake = minute_of(routine.wake)
                ring = datetime.combine(date, time(wake // 60, wake % 60), tzinfo=now.tzinfo)
                if ring > now and (found is None or ring < found[1]):
                    found = (routine, ring)
            if found:
                return found
        return None

    def by_hand(self, again: bool = False, timed: bool = False) -> list[Startable]:
        """The routines that can be started by hand today, with who can still do them
        (who_left.py; `timed`, also the ones that ring at a time, for parents). A race
        once each a day, unless a parent starts it `again` (one started by mistake, 26/11)."""
        now = self._clock.now()
        day = app_day(now)
        return self._who_left.startable(
            self._live(), day, WEEKDAYS[day.weekday()], _minute(now), timed=timed, again=again
        )

    def start(self, routine_id: str, kids: list[str], again: bool = False) -> None:
        """Start a routine by hand with the children who have come home (`again`: a race run today, by a parent)."""
        found = next((s for s in self.by_hand(again, timed=True) if s.routine.id == routine_id), None)
        if found is None:
            raise NotFoundError("No routine to start by hand today with that id")
        if not kids or any(k not in {c.id for c in found.missing} for k in kids):
            raise InvalidError("Choose who has come home, among the routine's children who have not done it")
        routine, now = found.routine, self._clock.now()
        day = app_day(now)
        self._runs.clear(day, routine_id)
        # After "3, 2, 1, ¡YA!", or "Va a empezar la misión…" and 5, 4, 3, 2, 1 (rutina-inicio.html)
        started = now + timedelta(seconds=START_SECONDS if routine.racing else INICIO_SECONDS)
        timed = not self._routines.get(routine_id).manual  # one that rings at a time, for who is left
        self._runs.set(day, routine_id, started_at=started, kids=json.dumps(kids), by_hand=1 if timed else None)
        for kid in kids:  # the mission's hours rule, but starting it by hand opens it (links.py)
            self._days.open_for_routine(kid, routine.mission_id)
        self._events.routine_did("routine_started", routine.name)

    def who(self, routine_id: str) -> tuple[list[Child], set[str]]:
        """¿Quién está? (rutinas-flexibles.html): the children of the routine going on's mission, and who is in it."""
        current = self._current(routine_id)
        theirs = self._missions.get(current.routine.mission_id).kids
        here = json.loads(current.run["kids"]) if current.run["kids"] else current.routine.kids
        return [c for c in self._children.list() if c.id in theirs], set(here)

    def set_who(self, routine_id: str, kids: list[str]) -> None:
        """A parent takes children out of the routine going on, or puts them back: they lose
        nothing, their mission stays as it is. Nobody left: it is finished."""
        children, _ = self.who(routine_id)
        if any(k not in {c.id for c in children} for k in kids):
            raise InvalidError("Only children of its mission")
        if not kids:
            return self.finish(routine_id)
        self._runs.set(self.current_day(), routine_id, kids=json.dumps([c.id for c in children if c.id in kids]))

    def note(  # noqa: C901 (to split)
        self,
        routine_id: str,
        kind: str,
        *,
        part: int | None = None,
        seconds: int | None = None,
        early: bool = False,
        phase: str | None = None,
    ) -> None:
        """What the screen tells: it rang, someone stopped it, a part or the goal came, it was
        hidden on a device (or shown again), or (started by hand) it ended: its time is up then,
        so it is no longer on."""
        if kind == "ended":
            routine = self._routines.get(routine_id)
            if routine is None:
                raise NotFoundError("Routine not found")
            if routine.manual:
                self._runs.clear(app_day(self._clock.now()), routine_id)
            else:  # rang at its time, then by hand for who was left: over today (it may go again for others)
                self._runs.set(app_day(self._clock.now()), routine_id, finished_at=self._clock.now())
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
            if early:  # everyone signed in the last part: it is over for today (04/11)
                self._runs.set(day, routine.id, finished_at=now)
            self._events.routine_did("routine_goal", routine.name, early=early)
        elif kind == "closed":  # hidden on one device only (16/11): the others go on, nothing to keep
            self._events.routine_did("routine_closed", routine.name)
        elif kind == "reopened":  # shown again on that device
            self._events.routine_did("routine_reopened", routine.name)

    def finish(self, routine_id: str) -> None:
        """Done for today: it does not come back until tomorrow (parents only)."""
        current = self._current(routine_id)
        self._runs.set(current.day, routine_id, finished_at=self._clock.now())
        self._events.routine_did("routine_finished", current.routine.name)

    def pause(self, routine_id: str, paused: bool) -> None:
        """Started by hand, a parent pauses it (its time stands still) or lets it go on
        (18/11): then it starts that much later, so it goes on where it was."""
        current = self._current(routine_id)
        run, now = current.run, self._clock.now()
        if current.started is None:
            raise ConflictError("Only a routine started by hand can be paused")
        if paused and not run["paused_at"]:
            self._runs.set(current.day, routine_id, paused_at=now)
        elif not paused and run["paused_at"]:
            started = datetime.fromisoformat(run["started_at"]) + (now - datetime.fromisoformat(run["paused_at"]))
            self._runs.set(current.day, routine_id, started_at=started, paused_at=None)
        else:
            return
        self._events.routine_did("routine_paused" if paused else "routine_resumed", current.routine.name)

    def current_day(self) -> date:
        """Today, by the household's clock (a day may start after midnight)."""
        return app_day(self._clock.now())

    def _current(self, routine_id: str) -> Current:
        current = self.current()
        if current is None or current.routine.id != routine_id:
            raise ConflictError("That routine is not going on now")
        return current

    def people(self, routine: Routine, trial: bool = False) -> list[Person]:
        return self._people.of(routine, trial)

    def pace(self, routine: Routine) -> Pace | None:
        """A race: the alien trains with this routine's last races."""
        return pace_of(self._races.recent(routine.id, RECORD_RACES)) if routine.racing else None

    def _everyone_off(self, routine: Routine) -> bool:
        return self._people.everyone_off(routine)


def _with_kids(routine: Routine, run: dict) -> Routine:
    """The routine with who is in it today, if they were chosen (by hand, or ¿Quién está?)."""
    return routine.model_copy(update={"kids": tuple(json.loads(run["kids"]))}) if run["kids"] else routine


def _minute(moment: datetime) -> float:
    """Minute of the day, with seconds."""
    return moment.hour * 60 + moment.minute + moment.second / 60
