"""Modo carrera (modo-carrera.html): a routine started by hand whose parts end when every
child who has their task has done it. The screen moves the race on (each child marks their
task on their own mission); here, how it ends: the time it took against the ghost, the
extra stars and the parent who checks before they are given. Running out of time is in
RoutinesService.current (the race is lost there, whoever is looking)."""

import json
from datetime import datetime

from app.children.repository import ChildrenRepository
from app.clock import Clock
from app.errors import ConflictError, NotFoundError
from app.events.service import EventLog
from app.routines.race_legs import race_legs
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
        """The last raced task is done: the flag (carrera-divertida.html). How it went, against
        the alien, with its cheers and turbos; its extra stars go to every child who ran it,
        now or once a parent checks. With a landing still to do, the routine goes on; asked
        again (another tablet, a reload), the same result."""
        current = self._racing(routine_id)
        legs = race_legs(current.routine, current.people, datetime.fromisoformat(current.run["started_at"]))
        if legs.flag_at is None:
            raise ConflictError("Somebody still has tasks left")
        routine, race = current.routine, current.routine.race
        done = next((r for r in self._races.of_day(current.day) if r["routine_id"] == routine_id), None)
        if done is not None:
            return done
        took = legs.race_seconds(legs.flag_at) / 60
        planned = max(1, planned_minutes(routine, current.people))
        turbos = legs.turbos(current.pace.ghost)
        result = outcome(took - stumbled_minutes(current.run, len(turbos)), planned, current.pace)
        stars = stars_for(race, result)
        waits = bool(stars) and race.review
        race_id = self._races.add(
            current.day,
            routine,
            [p.child for p in current.people],
            planned_seconds=planned * 60,
            took_seconds=round(took * 60),
            outcome=result,
            stars=stars,
            at=self._clock.now(),
            given=None if waits else bool(stars),
            ghost_share=current.pace.ghost,
            tasks=legs.tasks(),
        )
        if stars and not waits:
            self._give(self._races.get(race_id))
        if all(leg.ends for leg in legs.landing):
            self._routines.note(routine_id, "ended", early=True)
        self._events.routine_did(f"race_{result}", routine.name, part=_detail(took, planned, stars))
        return self._races.get(race_id)

    def _racing(self, routine_id: str):
        current = self._routines.current()
        if current is None or current.routine.id != routine_id or current.started is None or not current.routine.racing:
            raise ConflictError("That race is not going on now")
        return current

    def cheer(self, routine_id: str, child_id: str, part_id: str) -> list[str]:
        """«¡Ánimo, equipo!»: a child who did their task, or does not have it, cheers the
        ones still on it; the alien stumbles. Once per child and task. Today's cheers."""
        current = self._racing(routine_id)
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
        """A parent checked it: «Todo OK» gives its extra stars (not giving them is still
        possible, though the parents' screen no longer offers it). Only today's."""
        race = self._waiting(race_id)
        if race["redo"]:
            raise ConflictError("Some tasks must be done again first")
        return self._checked(race, give, f"+{race['stars']} ★" if give else "sin estrellas extra")

    def redo(self, race_id: int, task_ids: list[str]) -> dict:
        """The judges send some tasks to be done again (the parent says it in person): the
        stars wait until it is done, and that race no longer trains the alien."""
        race = self._waiting(race_id)
        known = {task["id"] for task in race["tasks"] or []}
        if not task_ids or any(task not in known for task in task_ids):
            raise NotFoundError("No such task in that race")
        self._races.set_redo(race_id, task_ids)
        names = [task["name"] for task in race["tasks"] if task["id"] in task_ids]
        self._events.routine_did("race_redo", race["routine_name"], part=", ".join(names))
        return self._races.get(race_id)

    def fixed(self, race_id: int) -> dict:
        """«Ya está»: what had to be done again was done. Its extra stars, given."""
        race = self._waiting(race_id)
        if not race["redo"]:
            raise ConflictError("Nothing to do again in that race")
        return self._checked(race, True, f"repasada · +{race['stars']} ★")

    def _waiting(self, race_id: int) -> dict:
        race = self._races.get(race_id)
        if race is None or race["day"] != self._routines.current_day().isoformat():
            raise NotFoundError("No race to check today with that id")
        if race["given"] is not None or not race["stars"]:
            raise ConflictError("That race was already checked")
        return race

    def _checked(self, race: dict, give: bool, detail: str) -> dict:
        self._races.reviewed(race["id"], give, self._clock.now())
        race = self._races.get(race["id"])
        if give:
            self._give(race)
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
