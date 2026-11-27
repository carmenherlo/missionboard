"""Rutinas de hoy, flexibles (rutinas-flexibles.html, 27/11): a routine of today can be
started by hand while some child of its mission has not done it, whether they did it on
their own or with the routine. One that rings at a time, only once it is over (or finished);
then it goes as one by hand, with the clock. Who did it already comes greyed out; in a race,
also who raced it today, unless a parent starts it `again`."""

from dataclasses import dataclass
from datetime import date

from app.children.repository import Child, ChildrenRepository
from app.missions.repository import MissionsRepository
from app.routines.model import Routine
from app.routines.races_repository import RacesRepository
from app.routines.repository import RunsRepository
from app.routines.timed_memory import as_by_hand
from app.today.service import DONE, OFF, DayService


@dataclass(frozen=True)
class Startable:
    routine: Routine  # as it goes by hand today
    kids: list[Child]  # its mission's children
    done: frozenset[str]  # who cannot be chosen: their mission done or let off today (or raced)

    @property
    def missing(self) -> list[Child]:
        return [c for c in self.kids if c.id not in self.done]


class WhoLeft:
    def __init__(
        self,
        children: ChildrenRepository,
        days: DayService,
        missions: MissionsRepository,
        runs: RunsRepository,
        races: RacesRepository,
    ):
        self._children = children
        self._days = days
        self._missions = missions
        self._runs = runs
        self._races = races

    def startable(
        self, routines: list[Routine], day: date, weekday: str, minute: float, *, timed: bool, again: bool
    ) -> list[Startable]:
        """`timed`: also the ones that ring at a time (only parents start those by hand)."""
        children = self._children.list()
        theirs = {m.id: m.kids for m in self._missions.list()}
        raced = {(race["routine_id"], kid["id"]) for race in self._races.of_day(day) for kid in race["kids"]}
        found = []
        for stored in routines:
            if not stored.goes_on(weekday):
                continue
            routine = stored.on(weekday)
            if not routine.manual:
                run = self._runs.get(day, routine.id)
                if not timed or not (run["finished_at"] or run["by_hand"] or minute >= routine.ends):
                    continue  # not over yet: it rings at its time
                routine = as_by_hand(routine)
            kids = [c for c in children if c.id in theirs.get(routine.mission_id, ())]
            done = set() if again else {c.id for c in kids if self._did(c.id, routine)}
            if routine.racing and not again:
                done |= {c.id for c in kids if (routine.id, c.id) in raced}  # a race, once each a day
            if any(c.id not in done for c in kids):
                found.append(Startable(routine, kids, frozenset(done)))
        return found

    def _did(self, child_id: str, routine: Routine) -> bool:
        """Their mission today is done or let off, or they have nothing of it today."""
        item = next((m for m in self._days.today(child_id).missions if m.mission.id == routine.mission_id), None)
        return item is None or item.state in (DONE, OFF)
