"""A routine (see service.py): it rings at its wake-up time and then guides part
after part, with the voice and a clock, until its goal. Its parts are its mission's
tasks (see repository.py for what is stored and what comes from the mission)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.missions.repository import WEEKDAYS
from app.routines.race_rules import Race
from app.routines.timing import card_positions, hhmm, minute_of, music_kept, settled
from app.settings import TIME, time_from_yaml_number


class PartStep(BaseModel):
    """A step of the part's task that some child of the routine has on."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    text: str
    image: str | None = None


class Part(BaseModel):
    """A part of the routine: one of the mission's tasks. It lasts its minutes, one part
    right after the other; only the first has a time of its own ("at")."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str = Field(pattern=r"^[\w-]{1,64}$")  # the task's
    at: str | None = Field(default=None, pattern=TIME)
    minutes: int = Field(ge=1, le=180)
    say: str | None = None  # a sentence of its own instead of "Comienza el aseo. Contiene: …"
    spoken: str | None = Field(default=None, max_length=60)  # how the voice names it: "el aseo"
    warnings: tuple[int, ...] | None = None  # minutes before the end; None: the default
    # In a race (modo-carrera.html), "sin prisa": "¡Hecho!" only after these minutes (at most, all of it).
    slow_minutes: int | None = Field(default=None, ge=1, le=180)
    # From the mission, when it is read (see resolved):
    text: str = ""  # the task's text, as on screen
    name: str = "-"  # as the voice says it, inside sentences
    image: str | None = None
    image_suggested: bool = False
    days: tuple[str, ...] = tuple(WEEKDAYS)  # the days its task is on
    steps: tuple[PartStep, ...] = ()

    _at = field_validator("at", mode="before")(time_from_yaml_number)


STORED_PART = ("id", "at", "minutes", "say", "spoken", "warnings", "slow_minutes")


class Goal(BaseModel):
    """Where the routine ends, at 07:45: "¡Es hora de irse al cole!". No name since
    rutinas-5 (the voice says "Quedan cinco minutos para terminar"). Before it, from
    the end of the last part, `check_minutes` to check the missions (rutinas-6): as
    soon as every child has done theirs, the goal comes and the routine is over.
    Started by hand (18/11), no `at`: it comes after the parts and the checking."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    image: str | None = None
    at: str | None = Field(default=None, pattern=TIME)  # None: started by hand
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
    mission_id: str
    name: str = "-"  # the mission's
    image: str | None = None  # the mission's
    days: tuple[str, ...] = tuple(WEEKDAYS)  # always within the mission's
    kids: tuple[str, ...] = ()  # who follows it (child ids); empty: every child, also the ones added later
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
    last_countdown: str | None = Field(default=None, max_length=200)  # ten seconds before the last part ends
    early_goal: str | None = Field(default=None, max_length=200)  # everyone signed before the goal
    # Before a part ends, the voice says "para que acabe el aseo" ("end") or "para que
    # empiece vestirse", the next one ("next", 04/11).
    warn_about: Literal["end", "next"] = "end"
    music: tuple[Music, ...] = ()
    race: Race | None = None  # None: its parts go by the clock (only by hand it can be a race)
    timed: dict | None = None  # started by hand: its times put away till it rings again (timed_memory.py)

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
        """How long a routine started by hand lasts, in minutes (its checking too)."""
        return sum(part.minutes for part in self.parts) + (self.goal.check_minutes if self.goal else 0)

    @property
    def racing(self) -> bool:
        """A race: only started by hand (once started, it has times like any other)."""
        return self.race is not None

    @property
    def parts_minutes(self) -> int:
        """How long its parts last, one after the other (in a race, until the flag)."""
        return sum(part.minutes for part in self.parts)

    def lengthened(self, extra: dict[str, int]) -> "Routine":
        """Started by hand, with the minutes a parent added to (or took from) some parts today."""
        if not extra:
            return self
        doc = self.to_doc()
        for part in doc["parts"]:
            part["minutes"] = max(1, part["minutes"] + extra.get(part["id"], 0))
        return Routine.model_validate(doc)

    def started_at(self, minute: int) -> "Routine":
        """A routine started by hand, as if it rang at `minute` with its first part right then."""
        doc = self.to_doc()
        doc["wake"] = hhmm(minute % (24 * 60))
        doc["parts"][0]["at"] = doc["wake"]
        if doc.get("goal"):  # after the parts and the checking (18/11)
            doc["goal"]["at"] = hhmm((minute + self.length) % (24 * 60))
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

    def goes_on(self, weekday: str) -> bool:
        """It is one of its days, and some task is on that day."""
        return weekday in self.days and any(weekday in part.days for part in self.parts)

    def on(self, weekday: str) -> "Routine":
        """The routine as it goes that day of the week (see goes_on): without the tasks
        that are not on that day, its pinned time still in place, and its offset applied."""
        kept = [part for part in self.parts if weekday in part.days]
        routine = self
        if len(kept) != len(self.parts):
            doc = self.to_doc()
            first_at = doc["parts"][0]["at"]
            doc["parts"] = [p for p in doc["parts"] if weekday in p["days"]]
            for part in doc["parts"]:
                part["at"] = None
            doc["parts"][0]["at"] = first_at
            routine = Routine.model_validate(music_kept(settled(doc)))
        return routine.shifted(self.offsets.get(weekday, 0))

    def timeline(self) -> list[tuple[Part, int, int]]:
        """Each part with its start and end, in minutes of the day (started by hand:
        in minutes from when it starts)."""
        if self.wake is None:
            if any(part.at for part in self.parts) or (self.goal and self.goal.at) or self.offsets or self.notices:
                raise ValueError(f"{self.id!r} is started by hand: no times of its own")
            if self.anchor == "end":
                raise ValueError(f"{self.id!r} is started by hand: it cannot end at a time")
            timed, start = [], 0
            for part in self.parts:
                timed.append((part, start, start + part.minutes))
                start += part.minutes
            return timed
        if self.parts[0].at is None or (self.goal and self.goal.at is None):
            raise ValueError(f"the first part and the goal of {self.id!r} need a time of their own (at)")
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
        return (
            minute_of(self.goal.at)
            if self.goal and self.goal.at
            else self.timeline()[-1][2] + (self.goal.check_minutes if self.goal else 0)
        )

    def overlaps(self, other: "Routine") -> bool:
        """Both ring on some day and their times cross that day (by hand: never)."""
        if self.manual or other.manual:
            return False
        for day in set(self.days) & set(other.days):
            if not self.goes_on(day) or not other.goes_on(day):
                continue
            mine, theirs = self.on(day), other.on(day)
            if minute_of(mine.wake) < theirs.ends and minute_of(theirs.wake) < mine.ends:
                return True
        return False

    def to_doc(self) -> dict:
        return self.model_dump(mode="json")
