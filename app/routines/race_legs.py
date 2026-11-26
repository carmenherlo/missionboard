"""Where a race is (carrera-divertida.html, 26/11), from when each child pressed «¡Hecho!»:
each task one after the other, when it started (the one before ended) and ended (the last
of its children marked it). A «con cuidado» task in the middle is a pit stop: the race
stands still while it lasts. The flag comes after the last raced task; the «con cuidado»
ones after it are the landing. A raced task done faster than the alien would: a turbo."""

from dataclasses import dataclass
from datetime import datetime

from app.routines.race_rules import careful


@dataclass(frozen=True)
class Leg:
    part: object  # the routine's Part
    landing: bool  # «con cuidado» after the last raced task
    starts: datetime | None  # None: the one before is not over yet
    ends: datetime | None  # None: somebody still has it to do

    @property
    def careful(self) -> bool:
        return careful(self.part)

    def seconds(self, now: datetime) -> float:
        """How long it has gone on (0 if it has not started)."""
        if self.starts is None:
            return 0.0
        return max(0.0, ((self.ends or now) - self.starts).total_seconds())


@dataclass(frozen=True)
class RaceLegs:
    legs: list[Leg]
    started: datetime

    @property
    def raced(self) -> list[Leg]:
        return [leg for leg in self.legs if not leg.careful]

    @property
    def flag_at(self) -> datetime | None:
        """When the last raced task ended (None: not yet)."""
        raced = self.raced
        if not raced or any(leg.ends is None for leg in raced):
            return None
        return raced[-1].ends

    @property
    def landing(self) -> list[Leg]:
        return [leg for leg in self.legs if leg.landing]

    def boxes_seconds(self, now: datetime) -> float:
        """How long the race stood still in its pit stops until `now`."""
        stops = [leg for leg in self.legs if leg.careful and not leg.landing]
        return sum(leg.seconds(min(now, leg.ends or now)) for leg in stops)

    def race_seconds(self, now: datetime) -> float:
        """The race's own time until `now` (or until the flag): pit stops left out."""
        until = min(now, self.flag_at or now)
        return max(0.0, (until - self.started).total_seconds() - self.boxes_seconds(until))

    def turbos(self, ghost: float) -> list[str]:
        """The raced tasks done faster than the alien would (its minutes at its pace)."""
        return [leg.part.id for leg in self.raced if leg.ends and leg.seconds(leg.ends) < leg.part.minutes * 60 * ghost]

    def tasks(self) -> list[dict]:
        """How each task went, for the judges."""
        return [
            {
                "id": leg.part.id,
                "name": leg.part.text,
                "minutes": leg.part.minutes,
                "seconds": round(leg.seconds(leg.ends)) if leg.ends else None,
                "careful": leg.careful,
            }
            for leg in self.legs
        ]


def race_legs(routine, people, started: datetime) -> RaceLegs:
    """The tasks some child running it has, in order, with their times."""
    having_parts = [
        (part, [p for p in people if part.id in p.mission["tasks"]])
        for part in routine.parts
        if any(part.id in p.mission["tasks"] for p in people)
    ]
    last_raced = max((i for i, (part, _) in enumerate(having_parts) if not careful(part)), default=-1)
    legs, starts = [], started
    for index, (part, having) in enumerate(having_parts):
        ends = None
        if starts is not None and all(p.mission["tasks"][part.id] for p in having):
            marks = [p.mission.get("done_at", {}).get(part.id) for p in having]
            times = [datetime.fromisoformat(at) for at in marks if at]
            ends = max([starts, *times])  # never before it started (a task marked early)
        legs.append(Leg(part, careful(part) and index > last_raced, starts, ends))
        starts = ends
    return RaceLegs(legs, started)
