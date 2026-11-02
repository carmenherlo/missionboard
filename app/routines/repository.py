"""Routines in config.yaml (`routines`) and what happened to each one each day (SQLite).

A routine is a talking schedule (see service.py): it rings at its wake-up
time and then guides part after part, with the voice and a clock, until its
goal. Ported from the old app (an earlier version, app/alarms.py), where
it was tested at home.
"""

from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.missions.repository import WEEKDAYS
from app.settings import TIME, time_from_yaml_number
from app.storage import db
from app.storage.config_store import ConfigStore


def minute_of(hhmm: str) -> int:
    """ "06:50" → 410 (minute of the day)."""
    hours, minutes = map(int, hhmm.split(":"))
    return hours * 60 + minutes


def hhmm(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"


class Part(BaseModel):
    """A part of the routine: breakfast, washing… It starts at its own time ("at") or
    right after the previous one, and lasts its minutes."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    name: str = Field(min_length=1, max_length=60)  # with its article, as it is said: "el aseo"
    image: str | None = None
    at: str | None = Field(default=None, pattern=TIME)
    minutes: int = Field(ge=1, le=180)
    say: str | None = None  # a sentence of its own instead of "Comienza el aseo."
    tasks: tuple[str, ...] = ()
    warnings: tuple[int, ...] | None = None  # minutes before the end; None: the default
    check_mission: bool = False  # the kids must have done their mission by its end

    _at = field_validator("at", mode="before")(time_from_yaml_number)


class Goal(BaseModel):
    """What the routine leads to: "vuestra clase", at 07:45."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    name: str = Field(min_length=1, max_length=60)
    image: str | None = None
    at: str = Field(pattern=TIME)
    say: str = "¡A salir de casa!"

    _at = field_validator("at", mode="before")(time_from_yaml_number)


class Routine(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str = Field(pattern=r"^[\w-]{1,64}$")
    name: str = Field(min_length=1, max_length=40)
    days: tuple[str, ...] = tuple(WEEKDAYS)
    kids: tuple[str, ...] = ()  # child ids; empty: every child
    wake: str | None = Field(default=None, pattern=TIME)  # None: started by hand (R2)
    remind_every: int = Field(default=5, ge=0, le=30)
    mission: str | None = None  # each child's mission with this name (until R3 links one each)
    parts: tuple[Part, ...] = Field(min_length=1)
    goal: Goal | None = None

    _wake = field_validator("wake", mode="before")(time_from_yaml_number)

    @field_validator("days")
    @classmethod
    def known_days(cls, days):
        if any(day not in WEEKDAYS for day in days):
            raise ValueError("days must be mon..sun")
        return days

    @model_validator(mode="after")
    def times_add_up(self) -> "Routine":
        self.timeline()  # raises ValueError if they do not
        return self

    def timeline(self) -> list[tuple[Part, int, int]]:
        """Each part with its start and end, in minutes of the day."""
        if self.wake is None:
            raise ValueError(f"{self.id!r} needs a wake-up time (routines by hand come later)")
        if self.parts[0].at is None:
            raise ValueError(f"the first part of {self.id!r} needs a time of its own (at)")
        timed = []
        previous_end = minute_of(self.wake)
        for part in self.parts:
            start = minute_of(part.at) if part.at else previous_end
            if start < previous_end:
                raise ValueError(f"{part.name!r} would start before the part before it ends")
            end = start + part.minutes
            timed.append((part, start, end))
            previous_end = end
        if self.goal and minute_of(self.goal.at) < previous_end:
            raise ValueError(f"the goal of {self.id!r} is before the routine ends")
        return timed

    @property
    def ends(self) -> int:
        return minute_of(self.goal.at) if self.goal else self.timeline()[-1][2]


class RoutinesRepository:
    """The `routines` list of config.yaml."""

    def __init__(self, store: ConfigStore):
        self._store = store

    def list(self) -> list[Routine]:
        return [Routine.model_validate(entry) for entry in self._store.load().get("routines") or []]


class RunsRepository:
    """What happened to each routine each day: started, stopped (the alarm),
    closed (until its next part) and finished (for the day)."""

    FIELDS = ("started_at", "stopped_at", "closed_phase", "finished_at")

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def get(self, day: date, routine_id: str) -> dict:
        with db.connect(self._data_dir) as conn:
            row = conn.execute(
                "SELECT * FROM routine_runs WHERE day = ? AND routine_id = ?", (day.isoformat(), routine_id)
            ).fetchone()
        return {name: row[name] if row else None for name in self.FIELDS}

    def set(self, day: date, routine_id: str, **values) -> None:
        assert set(values) <= set(self.FIELDS)
        values = {k: v.isoformat(timespec="seconds") if isinstance(v, datetime) else v for k, v in values.items()}
        columns = ", ".join(values)
        updates = ", ".join(f"{name} = excluded.{name}" for name in values)
        with db.connect(self._data_dir) as conn:
            conn.execute(
                f"INSERT INTO routine_runs (day, routine_id, {columns}) VALUES (?, ?, {', '.join('?' * len(values))})"
                f" ON CONFLICT (day, routine_id) DO UPDATE SET {updates}",
                (day.isoformat(), routine_id, *values.values()),
            )
