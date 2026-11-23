"""«± Tiempo» (modo-carrera.html, screen 6): with a routine started by hand going on, a
parent adds minutes to a part, or takes them, only today (some days tidying up takes
longer). The part going on and the ones to come; never below one minute, and the part
going on never ends before now. In a race the ghost and the flag move with it."""

import json

from app.errors import ConflictError, NotFoundError
from app.events.service import EventLog
from app.routines.repository import RunsRepository
from app.routines.service import RoutinesService


class ExtraTime:
    def __init__(self, routines: RoutinesService, runs: RunsRepository, events: EventLog):
        self._routines = routines
        self._runs = runs
        self._events = events

    def add(self, routine_id: str, part_id: str, minutes: int) -> int:
        """Add `minutes` (negative: take them) to a part; returns how many it has now."""
        current = self._routines.current()
        if current is None or current.routine.id != routine_id:
            raise ConflictError("That routine is not going on now")
        if current.started is None:
            raise ConflictError("Only a routine started by hand")
        routine = current.routine
        found = next(((i, p) for i, p in enumerate(routine.parts) if p.id == part_id), None)
        if found is None:
            raise NotFoundError("Part not found")
        index, part = found
        if self._over(current, index):
            raise ConflictError("That part is over")
        lowest = 1
        if not routine.racing:  # by the clock: the part going on cannot end before now
            starts = current.started + sum(p.minutes for p in routine.parts[:index])
            lowest = max(1, int(current.minute - starts) + 1)
        change = max(part.minutes + minutes, lowest) - part.minutes
        if change:
            extra = json.loads(current.run["extra"] or "{}")
            extra[part_id] = extra.get(part_id, 0) + change
            self._runs.set(current.day, routine_id, extra=json.dumps(extra))
            self._events.routine_did("routine_adjusted", routine.name, part=f"{part.text} {change:+d} min")
        return part.minutes + change

    @staticmethod
    def _over(current, index: int) -> bool:
        """By the clock: it has ended. In a race: everyone who has its task has done it."""
        routine = current.routine
        if routine.racing:
            part_id = routine.parts[index].id
            having = [p.mission["tasks"] for p in current.people if part_id in p.mission["tasks"]]
            return bool(having) and all(tasks[part_id] for tasks in having)
        return current.started + sum(p.minutes for p in routine.parts[: index + 1]) <= current.minute
