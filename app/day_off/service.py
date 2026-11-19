"""Días libres (dias-libres.html): "today it does not count", which is neither done nor
missed. A parent lets a child off a whole day, or some missions of it, today or on a day
to come (an outing is known before), with an optional sentence the voice says.

Who reads it, each on its own: the day (today/: state "off"), the daily prize (it does
not wait for them), the rachas (a whole day is a free tank; a mission off does not count)
and the routines (their goal does not wait for that child)."""

from datetime import date
from types import SimpleNamespace

from app.children.repository import ChildrenRepository
from app.clock import Clock, app_day
from app.day_off.repository import WHOLE_DAY, DayOffsRepository
from app.errors import InvalidError, NotFoundError
from app.events.service import EventLog
from app.missions.repository import MissionsRepository
from app.settings import SettingsRepository
from app.today.plan import missions_by_day


class DayOffService:
    def __init__(
        self,
        children: ChildrenRepository,
        missions: MissionsRepository,
        offs: DayOffsRepository,
        settings: SettingsRepository,
        clock: Clock,
        events: EventLog,
    ):
        self._children = children
        self._missions = missions
        self._offs = offs
        self._settings = settings
        self._clock = clock
        self._events = events

    def today(self) -> date:
        return app_day(self._clock.now(), self._settings.settings().day_starts_at)

    def day(self, child_id: str, day: date) -> dict:
        """What the child has that day and what of it is off."""
        child = self._children.require(child_id)
        off = self._offs.on(child.id, day)
        had = missions_by_day(self._missions.list(), child.id)(day)
        return {
            "child": child,
            "day": day,
            "whole": WHOLE_DAY in off,
            "phrase": next(iter(off.values()), ""),
            "missions": [(m, m.id in off) for m in self._missions.list() if m.id in had],
        }

    def set_day(self, child_id: str, day: date, whole: bool, missions: list[str], phrase: str) -> dict:
        """All that is off that day, at once (the window saves on every change)."""
        child = self._children.require(child_id)
        if day < self.today():
            raise InvalidError("A day gone by is let off from the week (Padres · Niño)")
        had = missions_by_day(self._missions.list(), child.id)(day)
        if set(missions) - had:
            raise NotFoundError("That mission is not theirs that day")
        before = self._offs.on(child.id, day)
        off = set(missions) | ({WHOLE_DAY} if whole else set())
        phrase = phrase.strip() if off else ""
        self._offs.replace(child.id, day, off, phrase, self._clock.now())
        self._log(child, day, before, off, phrase)
        return self.day(child_id, day)

    def _log(self, child, day: date, before: dict[str, str], off: set[str], phrase: str) -> None:
        when = SimpleNamespace(id=day.isoformat(), name=f"{day.day}/{day.month}")
        changes = {"phrase": phrase} if phrase else None
        if (WHOLE_DAY in off) != (WHOLE_DAY in before):
            self._events.config_changed(
                "day_off", "on" if WHOLE_DAY in off else "off", child=child, mission=when, changes=changes
            )
        names = {m.id: m.name for m in self._missions.list()}
        for mission_id in (off ^ set(before)) - {WHOLE_DAY}:
            self._events.config_changed(
                "mission_off",
                "on" if mission_id in off else "off",
                child=child,
                mission=SimpleNamespace(id=mission_id, name=names.get(mission_id, "")),
                changes={"day": when.name, **(changes or {})},
            )
