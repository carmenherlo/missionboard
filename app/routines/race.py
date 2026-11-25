"""Modo carrera (modo-carrera.html): a routine started by hand whose parts end when every
child who has their task has done it. The screen moves the race on (each child marks their
task on their own mission); here, how it ends: the time it took against the ghost, the
extra stars and the parent who checks before they are given. Running out of time is in
RoutinesService.current (the race is lost there, whoever is looking)."""

import json

from app.children.repository import ChildrenRepository
from app.clock import Clock
from app.errors import ConflictError, NotFoundError
from app.events.service import EventLog
from app.routines.race_rules import cheered, outcome, planned_minutes, stars_for, stumbled_minutes
from app.routines.races_repository import RacesRepository
from app.routines.repository import RunsRepository
from app.routines.service import RoutinesService
from app.stars.repository import StarsRepository


class RaceService:
    def __init__(
        self,
        routines: RoutinesService,
        races: RacesRepository,
        stars: StarsRepository,
        children: ChildrenRepository,
        clock: Clock,
        events: EventLog,
        runs: RunsRepository,
    ):
        self._runs = runs
        self._routines = routines
        self._races = races
        self._stars = stars
        self._children = children
        self._clock = clock
        self._events = events

    def end(self, routine_id: str) -> dict:
        """Everyone has done their tasks: the race is over. Its extra stars go to every child
        who ran it, now or once a parent checks."""
        current = self._routines.current()
        if current is None or current.routine.id != routine_id or current.started is None or not current.routine.racing:
            raise ConflictError("That race is not going on now")
        if not all(p.mission["completed"] for p in current.people):
            raise ConflictError("Somebody still has tasks left")
        routine, race = current.routine, current.routine.race
        took = current.minute - current.started
        planned = planned_minutes(routine, current.people)
        result = outcome(took - stumbled_minutes(current.run), planned, current.pace)  # its cheers count
        stars = stars_for(race, result)
        kids = [p.child for p in current.people]
        waits = bool(stars) and race.review
        now = self._clock.now()
        race_id = self._races.add(
            current.day,
            routine,
            kids,
            planned_seconds=planned * 60,
            took_seconds=round(took * 60),
            outcome=result,
            stars=stars,
            at=now,
            given=None if waits else bool(stars),
            ghost_share=current.pace.ghost,
        )
        if stars and not waits:
            self._give(self._races.get(race_id))
        self._routines.note(routine_id, "ended", early=True)
        self._events.routine_did(f"race_{result}", routine.name, part=_detail(took, planned, stars))
        return self._races.get(race_id)

    def cheer(self, routine_id: str, child_id: str, part_id: str) -> list[str]:
        """«¡Ánimo, equipo!»: a child who did their task, or does not have it, cheers the
        ones still on it; the alien stumbles. Once per child and task. Today's cheers."""
        current = self._routines.current()
        if current is None or current.routine.id != routine_id or current.started is None or not current.routine.racing:
            raise ConflictError("That race is not going on now")
        person = next((p for p in current.people if p.child.id == child_id), None)
        going = next(
            (
                part.id
                for part in current.routine.parts
                if any(part.id in p.mission["tasks"] and not p.mission["tasks"][part.id] for p in current.people)
            ),
            None,
        )
        if person is None or part_id != going or (person.mission or {}).get("tasks", {}).get(part_id) is False:
            raise ConflictError("Nobody to cheer there")
        cheers = cheered(current.run)
        if f"{part_id}:{child_id}" not in cheers:
            cheers.append(f"{part_id}:{child_id}")
            self._runs.set(current.day, routine_id, cheers=json.dumps(cheers))
        return cheers

    def to_review(self) -> list[dict]:
        """Today's races whose extra stars wait for a parent (Padres · Por dar)."""
        day = self._routines.current_day()
        return [r for r in self._races.of_day(day) if r["given"] is None and r["stars"]]

    def review(self, race_id: int, give: bool) -> dict:
        """A parent checked it: the extra stars, given or not. Only today's."""
        race = self._races.get(race_id)
        if race is None or race["day"] != self._routines.current_day().isoformat():
            raise NotFoundError("No race to check today with that id")
        if race["given"] is not None or not race["stars"]:
            raise ConflictError("That race was already checked")
        self._races.reviewed(race_id, give, self._clock.now())
        race = self._races.get(race_id)
        if give:
            self._give(race)
        detail = f"+{race['stars']} ★" if give else "sin estrellas extra"
        self._events.routine_did("race_reviewed", race["routine_name"], part=detail)
        return race

    def _give(self, race: dict) -> None:
        now = self._clock.now()
        for kid in race["kids"]:
            child = self._children.get(kid["id"])
            if child is not None:
                self._stars.give(child, race["stars"], self._routines.current_day(), now, reason="race")


def _detail(took: float, planned: int, stars: int) -> str:
    seconds = round(took * 60)
    text = f"{seconds // 60}:{seconds % 60:02d} de {planned}:00"
    return f"{text} · +{stars} ★" if stars else text
