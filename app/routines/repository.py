"""Routines in config.yaml (`routines`) and what happened to each one each day (SQLite).

A routine is a talking schedule (see service.py): it rings at its wake-up
time and then guides part after part, with the voice and a clock, until its
goal. Ported from the old app (an earlier version, app/alarms.py), where
it was tested at home.
"""

from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.missions.repository import WEEKDAYS
from app.settings import TIME, time_from_yaml_number
from app.storage import db
from app.storage.config_store import ConfigStore


def card_positions(doc: dict) -> dict[str, int]:
    """Where a song can start or end, in order: the alarm (-1), each part, the goal."""
    timed = doc.get("wake") is not None
    parts = doc.get("parts") or []
    cards = {part["id"]: index for index, part in enumerate(parts)}
    if timed and doc.get("alarm", True):
        cards["alarm"] = -1
    if timed and doc.get("goal"):
        cards["goal"] = len(parts)
    return cards


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

    id: str = Field(pattern=r"^[\w-]{1,64}$")
    name: str = Field(min_length=1, max_length=60)  # with its article, as it is said: "el aseo"
    image: str | None = None
    image_suggested: bool = False
    at: str | None = Field(default=None, pattern=TIME)
    minutes: int = Field(ge=1, le=180)
    say: str | None = None  # a sentence of its own instead of "Comienza el aseo."
    tasks: tuple[str, ...] = ()
    warnings: tuple[int, ...] | None = None  # minutes before the end; None: the default

    _at = field_validator("at", mode="before")(time_from_yaml_number)


class Goal(BaseModel):
    """Where the routine ends, at 07:45: "¡Es hora de irse al cole!". No name since
    rutinas-5 (the voice says "Quedan cinco minutos para terminar"). Before it, from
    the end of the last part, `check_minutes` to check the missions (rutinas-6): as
    soon as every child has done theirs, the goal comes and the routine is over."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    image: str | None = None
    at: str = Field(pattern=TIME)
    say: str = "¡Rutina terminada!"
    check_minutes: int = Field(default=0, ge=0, le=30)  # 0: no checking
    check_say: str | None = Field(default=None, max_length=200)  # None: "Es hora de revisar las misiones."

    _at = field_validator("at", mode="before")(time_from_yaml_number)


class Music(BaseModel):
    """A song in a routine (rutinas-4, section 3), like Scratch's "iniciar sonido": the
    routine never waits for it. From a card (`start`: "alarm", a part's id or "goal")
    to a card (`until`: a part's id or "goal", repeating until it ends; None: once)."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str = Field(pattern=r"^[\w-]{1,64}$")
    songs: tuple[str, ...] = Field(min_length=1)  # one after the other (04/11)
    start: str
    until: str | None = None
    after_voice: bool = False  # it waits until the voice has finished speaking (04/11)
    loud: bool = False  # at full volume, whatever the Música level: to wake up (04/11)


class Notice(BaseModel):
    """Said before the routine rings: "Es hora de despertar a los niños", 20 minutes before."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    minutes: int = Field(ge=1, le=180)
    say: str = Field(min_length=1, max_length=200)


class Routine(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str = Field(pattern=r"^[\w-]{1,64}$")
    name: str = Field(min_length=1, max_length=40)
    days: tuple[str, ...] = tuple(WEEKDAYS)
    kids: tuple[str, ...] = ()  # child ids; empty: every child, also the ones added later
    missions: dict[str, str | None] = {}  # each child's mission in this routine (by id)
    wake: str | None = Field(default=None, pattern=TIME)  # None: started by hand (R2)
    remind_every: int = Field(default=5, ge=0, le=30)
    # Which time stays put when the parts change: "start" (Empieza a las), or "end"
    # (Termina a las: the goal's time; the parts go one after the other up to it).
    anchor: Literal["start", "end"] = "start"
    alarm: bool = True  # the "rrring" (before or at its first part); off: a ding, for bedtime
    # Some days everything moves: {"tue": 15} rings and goes 15 minutes later on Tuesdays.
    offsets: dict[str, int] = {}
    notices: tuple[Notice, ...] = ()  # said before it rings (not by hand)
    parts: tuple[Part, ...] = Field(min_length=1)
    goal: Goal | None = None
    # Sentences of its own (rutinas-5, "Lo que dice la voz"); None: the usual one (texts.js).
    greeting: str | None = Field(default=None, max_length=200)  # the alarm, ringing before the first part
    last_countdown: str | None = Field(default=None, max_length=200)  # ten seconds before the last part ends
    early_goal: str | None = Field(default=None, max_length=200)  # everyone signed before the goal
    # Before a part ends, the voice says "para que acabe el aseo" ("end") or "para que
    # empiece vestirse", the next one ("next", 04/11).
    warn_about: Literal["end", "next"] = "end"
    music: tuple[Music, ...] = ()

    _wake = field_validator("wake", mode="before")(time_from_yaml_number)

    @field_validator("days")
    @classmethod
    def known_days(cls, days):
        if any(day not in WEEKDAYS for day in days):
            raise ValueError("days must be mon..sun")
        return days

    @field_validator("offsets")
    @classmethod
    def known_offsets(cls, offsets):
        if any(day not in WEEKDAYS or not -180 <= minutes <= 180 for day, minutes in offsets.items()):
            raise ValueError("offsets: mon..sun, up to 180 minutes either way")
        return {day: minutes for day, minutes in offsets.items() if minutes}

    @model_validator(mode="after")
    def music_fits(self) -> "Routine":
        """Each song from a card to the same or a later one, and no two at a time."""
        cards = card_positions(self.to_doc())
        end = -2
        for music in sorted(self.music, key=lambda m: cards.get(m.start, -9)):
            start = cards.get(music.start)
            until = start if music.until is None else cards.get(music.until)
            if start is None or until is None or until < start or music.until == "alarm" or start <= end:
                raise ValueError(f"the songs of {self.id!r} do not fit its cards")
            end = until
        return self

    @model_validator(mode="after")
    def times_add_up(self) -> "Routine":
        self.timeline()  # raises ValueError if they do not
        for minutes in self.offsets.values():  # moved, it stays within its day
            if self.manual or minute_of(self.wake) + minutes < 0 or self.ends + minutes > 24 * 60:
                raise ValueError(f"{self.id!r} would move out of its day")
        return self

    @property
    def manual(self) -> bool:
        """Started by hand (no wake-up time): its parts go one after the other from then on."""
        return self.wake is None

    @property
    def length(self) -> int:
        """How long a routine started by hand lasts, in minutes."""
        return sum(part.minutes for part in self.parts)

    def started_at(self, minute: int) -> "Routine":
        """A routine started by hand, as if it rang at `minute` with its first part right then."""
        doc = self.to_doc()
        doc["wake"] = hhmm(minute % (24 * 60))
        doc["parts"][0]["at"] = doc["wake"]
        return Routine.model_validate(doc)

    def shifted(self, minutes: int) -> "Routine":
        """The same routine with every time moved by `minutes` (wrapping round midnight)."""
        if not minutes:
            return self
        shift = lambda time: hhmm((minute_of(time) + minutes) % (24 * 60))  # noqa: E731
        doc = self.to_doc()
        doc["wake"] = doc["wake"] and shift(doc["wake"])
        doc["offsets"] = {}
        for part in doc["parts"]:
            part["at"] = part["at"] and shift(part["at"])
        if doc.get("goal"):
            doc["goal"]["at"] = shift(doc["goal"]["at"])
        return Routine.model_validate(doc)

    def on(self, weekday: str) -> "Routine":
        """The routine as it goes that day of the week (its offset applied)."""
        return self.shifted(self.offsets.get(weekday, 0))

    def timeline(self) -> list[tuple[Part, int, int]]:
        """Each part with its start and end, in minutes of the day (started by hand:
        in minutes from when it starts)."""
        if self.wake is None:
            if any(part.at for part in self.parts) or self.goal or self.offsets or self.notices or self.anchor == "end":
                raise ValueError(f"{self.id!r} is started by hand: no times of its own, no goal")
            timed, start = [], 0
            for part in self.parts:
                timed.append((part, start, start + part.minutes))
                start += part.minutes
            return timed
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
        checked = previous_end + (self.goal.check_minutes if self.goal else 0)  # the checking, after the parts
        if self.goal and minute_of(self.goal.at) < checked:
            raise ValueError(f"the goal of {self.id!r} is before the routine ends")
        if self.anchor == "end" and (
            not self.goal or any(part.at for part in self.parts[1:]) or minute_of(self.goal.at) != checked
        ):
            raise ValueError(f"{self.id!r} ends at its goal: its parts go one after the other up to it")
        return timed

    @property
    def starts(self) -> int:
        """When its first part starts, in minutes of the day."""
        return self.timeline()[0][1]

    @property
    def alarm_before(self) -> int:
        """How many minutes before its first part it rings."""
        return (self.starts - minute_of(self.wake)) % (24 * 60)

    @property
    def ends(self) -> int:
        """When it is over, in minutes of the day (started by hand: from when it starts)."""
        return minute_of(self.goal.at) if self.goal else self.timeline()[-1][2]

    def overlaps(self, other: "Routine") -> bool:
        """Both ring on some day and their times cross that day (by hand: never)."""
        if self.manual or other.manual:
            return False
        for day in set(self.days) & set(other.days):
            mine, theirs = self.on(day), other.on(day)
            if minute_of(mine.wake) < theirs.ends and minute_of(theirs.wake) < mine.ends:
                return True
        return False

    def to_doc(self) -> dict:
        return self.model_dump(mode="json")


class RoutinesRepository:
    """The `routines` list of config.yaml."""

    def __init__(self, store: ConfigStore):
        self._store = store

    def atomic(self):
        return self._store.edit()

    def list(self) -> list[Routine]:
        return [Routine.model_validate(entry) for entry in self._store.load().get("routines") or []]

    def get(self, routine_id: str) -> Routine | None:
        return next((r for r in self.list() if r.id == routine_id), None)

    def add(self, routine: Routine) -> None:
        with self._store.edit() as doc:
            doc.setdefault("routines", []).append(routine.to_doc())

    def update(self, routine: Routine) -> None:
        with self._store.edit() as doc:
            doc["routines"] = [routine.to_doc() if r["id"] == routine.id else r for r in doc["routines"]]

    def remove(self, routine_id: str) -> None:
        with self._store.edit() as doc:
            doc["routines"] = [r for r in doc["routines"] if r["id"] != routine_id]


class RunsRepository:
    """What happened to each routine each day: started, stopped (the alarm),
    closed (until its next part) and finished (for the day)."""

    FIELDS = ("started_at", "stopped_at", "closed_phase", "finished_at", "kids")

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def get(self, day: date, routine_id: str) -> dict:
        with db.connect(self._data_dir) as conn:
            row = conn.execute(
                "SELECT * FROM routine_runs WHERE day = ? AND routine_id = ?", (day.isoformat(), routine_id)
            ).fetchone()
        return {name: row[name] if row else None for name in self.FIELDS}

    def clear(self, day: date, routine_id: str) -> None:
        """Forget today's run (a routine started by hand that ended: it can start again)."""
        with db.connect(self._data_dir) as conn:
            conn.execute("DELETE FROM routine_runs WHERE day = ? AND routine_id = ?", (day.isoformat(), routine_id))

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
