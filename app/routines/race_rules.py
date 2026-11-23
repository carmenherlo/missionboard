"""The rules of a race (modo-carrera.html), apart from how it is kept or run: its
settings, the ghost and "muy rápido", and the extra stars for how it went."""

from pydantic import BaseModel, ConfigDict, Field


class Race(BaseModel):
    """A routine started by hand, as a race (modo-carrera.html): each part ends when every
    child who has its task has done it. The ghost gets to the end a little before the
    routine's time; beating it gives every child `on_time` extra stars, and finishing very
    fast, `fast`. A parent checks before they are given (`review`)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    on_time: int = Field(default=1, ge=0, le=10)
    fast: int = Field(default=2, ge=0, le=10)
    review: bool = True


GHOST_SHARE = 0.9  # the ghost gets to the flag a little before the routine's time
FAST_SHARE = 0.8  # "muy rápido"


def outcome(took_minutes: float, planned_minutes: float) -> str:
    """fast, won (it beat the ghost) or slow (finished, but the ghost got there first)."""
    if took_minutes <= planned_minutes * FAST_SHARE:
        return "fast"
    return "won" if took_minutes <= planned_minutes * GHOST_SHARE else "slow"


def stars_for(race: Race, result: str) -> int:
    return {"fast": max(race.fast, race.on_time), "won": race.on_time}.get(result, 0)


START_SECONDS = 6  # "3, 2, 1, ¡YA!" before its first part: it does not count


def planned_minutes(routine, people) -> int:
    """Its time, the flag: the parts that some child running it has (the others are skipped)."""
    having = [p for p in routine.parts if any(p.id in person.mission["tasks"] for person in people)]
    return sum(p.minutes for p in having) if people else routine.parts_minutes
