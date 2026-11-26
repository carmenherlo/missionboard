"""Whether a race goes on (RoutinesService.current), whoever is looking: until the flag,
unless its time runs out first (the race is lost: it ends there, and its mission closes
for its children at that moment); after the flag, while the landing lasts (carrera-divertida.html)."""

from datetime import date, datetime, timedelta

from app.events.service import EventLog
from app.routines.model import Routine
from app.routines.people import Person
from app.routines.race_legs import race_legs
from app.routines.race_rules import Pace, planned_minutes
from app.routines.races_repository import RacesRepository
from app.routines.repository import RunsRepository

LANDING_SPARE_MINUTES = 10  # after the flag: the landing's minutes and these (a tablet off)


class RaceFlag:
    def __init__(self, runs: RunsRepository, races: RacesRepository, events: EventLog):
        self._runs = runs
        self._races = races
        self._events = events

    def goes_on(self, routine: Routine, day: date, run: dict, people: list[Person], pace: Pace, now: datetime) -> bool:
        legs = race_legs(routine, people, datetime.fromisoformat(run["started_at"]))
        if legs.flag_at is not None:
            landing = sum(leg.part.minutes for leg in legs.landing)
            return now < legs.flag_at + timedelta(minutes=landing + LANDING_SPARE_MINUTES)
        planned = planned_minutes(routine, people) * 60
        if legs.race_seconds(now) < planned:
            return True
        flag = legs.started + timedelta(seconds=planned + legs.boxes_seconds(now))
        self._lost(routine, day, people, pace, planned, flag)
        return False

    def today(self, routine_id: str, day: date, run: dict) -> dict:
        """What the race's screen needs from before: its result once past the flag, and
        how many times the voice explained each new thing (it does it the first times)."""
        return {"result": self.result(routine_id, day, run), "tips": self._races.tips(routine_id)}

    def result(self, routine_id: str, day: date, run: dict) -> dict | None:
        """This run's race once past the flag (not an earlier one today: a parent may start it again)."""
        started = datetime.fromisoformat(run["started_at"])
        races = [r for r in self._races.of_day(day) if r["routine_id"] == routine_id]
        return next((r for r in reversed(races) if datetime.fromisoformat(r["at"]) >= started), None)

    def _lost(self, routine: Routine, day: date, people: list[Person], pace: Pace, planned: int, flag: datetime):
        """Its time is up and not everyone finished: once (the run is finished)."""
        self._runs.set(day, routine.id, finished_at=flag)
        self._races.add(
            day,
            routine,
            [p.child for p in people],
            planned_seconds=planned,
            took_seconds=None,
            outcome="lost",
            stars=0,
            at=flag,
            given=None,
            ghost_share=pace.ghost,
        )
        self._events.routine_did("race_lost", routine.name)
