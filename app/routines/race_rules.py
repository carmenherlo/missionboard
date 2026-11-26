"""The rules of a race (modo-carrera.html, carrera-estrategia.html), apart from how it is
kept or run: its settings, the alien that trains with the team's last races, the record and
the extra stars for how it went."""

import json
from dataclasses import dataclass
from statistics import median

from pydantic import BaseModel, ConfigDict, Field


class Race(BaseModel):
    """A routine started by hand, as a race (modo-carrera.html): each part ends when every
    child who has its task has done it. Beating the alien gives every child `on_time` extra
    stars, and one more if it is also their record. A parent checks before they are given
    (`review`)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    on_time: int = Field(default=1, ge=0, le=10)
    review: bool = True


FIRST_GHOST = 0.9  # no races yet: the alien gets to the flag at 90 % of the time
# It adjusts (carrera-divertida.html, 26/11) so the team wins about 2 of 3: after a lost race
# it runs slower than their usual; after one won, like it; after two won, a little faster.
AFTER_LOST, AFTER_WON, AFTER_TWO_WON = 1.05, 1.0, 0.95
GHOST_FASTEST, GHOST_SLOWEST = 0.6, 1.0
PACE_RACES = 5  # the alien runs like the team's last 5 races
RECORD_RACES = 10  # the record: the best of the last 10 (an old lucky day must not stay forever)
RECORD_STARS = 1  # beating the alien and the record: one more extra star
CHEER_SECONDS = 5  # «¡Ánimo, equipo!»: each cheer, the alien stumbles and loses this much
TURBO_SECONDS = 10  # a task done faster than the alien would: turbo, it loses this much
WON = ("record", "won")


@dataclass(frozen=True)
class Pace:
    """How fast this team is today, as shares of the race's time: the alien's and the record's."""

    ghost: float
    record: float | None  # None: no race finished yet


def _counts(race: dict) -> bool:
    """A race whose extra stars a parent refused, or whose tasks had to be done again, does
    not count (the alien does not learn cheating)."""
    return not (race["stars"] and race["given"] is False) and not race.get("redo")


def _training(counted: list[dict]) -> float:
    """How much faster than the team's usual the alien runs, from how the last races went."""
    last = [race.get("outcome") for race in counted[:2]]
    if last and last[0] not in WON:
        return AFTER_LOST
    return AFTER_TWO_WON if len(last) == 2 and all(o in WON for o in last) else AFTER_WON


def pace_of(past: list[dict]) -> Pace:
    """From this routine's past races (newest first): the alien runs like the last ones,
    faster or slower as the last ones went, and the record is the best of the last ones finished."""
    counted = [race for race in past if _counts(race)]
    shares = [1.0 if r["took_seconds"] is None else r["took_seconds"] / r["planned_seconds"] for r in counted]
    ghost = median(shares[:PACE_RACES]) * _training(counted) if shares else FIRST_GHOST
    finished = [s for s, r in zip(shares, counted, strict=True) if r["took_seconds"] is not None][:RECORD_RACES]
    return Pace(min(max(ghost, GHOST_FASTEST), GHOST_SLOWEST), min(finished) if finished else None)


def outcome(took_minutes: float, planned_minutes: float, pace: Pace) -> str:
    """record (it beat the alien and its best), won (it beat the alien) or slow (finished,
    but the alien got there first)."""
    share = took_minutes / planned_minutes
    if share > pace.ghost:
        return "slow"
    return "record" if pace.record is not None and share < pace.record else "won"


def stars_for(race: Race, result: str) -> int:
    if not race.on_time:
        return 0
    return {"record": race.on_time + RECORD_STARS, "won": race.on_time}.get(result, 0)


def cheered(run: dict) -> list[str]:
    """Today's cheers in a race: "task id:child id", once each."""
    return json.loads(run["cheers"] or "[]")


def stumbled_minutes(run: dict, turbos: int = 0) -> float:
    """How far behind the alien is from its cheers and the team's turbos."""
    return (len(cheered(run)) * CHEER_SECONDS + turbos * TURBO_SECONDS) / 60


def careful(part) -> bool:
    """«Con cuidado» (was «sin prisa»): not raced. In the middle, a pit stop (the race stands
    still while its tank fills); after the last raced task, the landing, past the flag."""
    return bool(part.slow_minutes)


def done_after(part) -> float:
    """In a race, the minutes before a task's «¡Hecho!» can be pressed: only a «con cuidado»
    task waits, while its tank fills; the others, none (25/11: a wait on every task was dropped)."""
    return min(part.slow_minutes, part.minutes) if part.slow_minutes else 0


START_SECONDS = 6  # "3, 2, 1, ¡YA!" before its first part: it does not count
INICIO_SECONDS = 10  # by hand with the clock: "Va a empezar la misión…" and 5, 4, 3, 2, 1


def planned_minutes(routine, people) -> int:
    """Its time, the flag: the raced parts that some child running it has (the others are
    skipped, and the «con cuidado» ones do not count: the race stands still in them)."""
    raced = [p for p in routine.parts if not careful(p)]
    if not people:
        return sum(p.minutes for p in raced)
    return sum(p.minutes for p in raced if any(p.id in person.mission["tasks"] for person in people))
