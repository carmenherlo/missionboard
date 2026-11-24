"""A routine going on: which one, today, now, its run and who does it (RoutinesService.current)."""

from dataclasses import dataclass
from datetime import date

from app.routines.model import Part, Routine
from app.routines.people import Person
from app.routines.race_rules import Pace

WARN_MINUTES = 1  # a task with no warnings of its own: "Queda un minuto…" (24/11: always, not a setting)


@dataclass
class Current:
    routine: Routine
    day: date
    minute: float  # minute of the day now, with seconds
    run: dict  # see RunsRepository
    people: list[Person]
    started: float | None = None  # started by hand: the minute of the day it started, with seconds
    pace: Pace | None = None  # a race: how fast the alien runs and the record

    def warnings(self, part: Part) -> list[int]:
        """When the voice warns before the part ends: its own, or else the default
        (only in parts longer than 2 minutes: the 10-second countdown is enough there)."""
        if part.warnings is not None:
            return list(part.warnings)
        return [WARN_MINUTES] if part.minutes > 2 else []
