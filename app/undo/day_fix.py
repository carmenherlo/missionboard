"""Arreglar un día (19/11): in Padres · Niño a parent taps a day of this week and says
what it was: «Lo hizo» (they forgot to sign: its missions done, with their stars, and its
tank full), «No lo hizo» (its missions undone, as UndoService does one) or «Libre» (the
whole day off). Done and not done only for this week's days up to today, while its
rocket has not taken off; a day ahead can only be let off. No gift card is won here:
the wheel is the child's."""

from datetime import date

from app.children.repository import ChildrenRepository
from app.clock import Clock
from app.day_off.repository import WHOLE_DAY, DayOffsRepository
from app.errors import InvalidError
from app.events.service import EventLog
from app.missions.repository import MissionsRepository
from app.settings import SettingsRepository
from app.streaks.service import StreaksService
from app.today.plan import missions_by_day
from app.today.repository import DayRepository
from app.undo.service import UndoService

CHOICES = ("done", "missed", "free")


class DayFix:
    def __init__(
        self,
        undo: UndoService,
        children: ChildrenRepository,
        missions: MissionsRepository,
        days: DayRepository,
        offs: DayOffsRepository,
        streaks: StreaksService,
        settings: SettingsRepository,
        clock: Clock,
        events: EventLog,
    ):
        self._undo = undo
        self._children = children
        self._missions = missions
        self._days = days
        self._offs = offs
        self._streaks = streaks
        self._settings = settings
        self._clock = clock
        self._events = events

    def fix(self, child_id: str, day: date, choice: str) -> None:
        if choice not in CHOICES:
            raise InvalidError("Choose done, missed or free")
        child = self._children.require(child_id)
        if choice == "free":
            self._streaks.set_free_day(child.id, day, True)
            return
        self._streaks.undo_check(child.id, day)  # this week, up to today, rocket not gone
        if WHOLE_DAY in self._offs.on(child.id, day):
            self._streaks.set_free_day(child.id, day, False)
        had = missions_by_day(self._missions.list(), child.id, self._offs.by_day(child.id))(day)
        done = self._days.completions(child.id).get(day.isoformat(), set())
        if choice == "done":
            self._mark_done(child, day, had - done)
        else:
            for mission_id in sorted(done):
                self._undo.undo(child.id, mission_id, day)

    def _mark_done(self, child, day: date, missing: set[str]) -> None:
        stars = self._settings.settings().stars_per_mission
        now = self._clock.now()
        for mission in (m for m in self._missions.list() if m.id in missing):
            if self._days.complete(day, child, mission, stars, now):
                changes = {"gift": stars, "day": f"{day.day}/{day.month}"}
                self._events.config_changed("mission", "marked_done", child=child, mission=mission, changes=changes)
        self._streaks.after_change(child.id, day)  # a week closed without this day opens again
