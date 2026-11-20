"""Deshacer una misión (dias-libres.html, section 6): a child checked tasks they had not
done and completed a mission. A parent undoes it, and with it all that hung from it:

- the mission: no longer done, its tasks unchecked (open again if its time is not over);
- its stars: out of the bank, never below 0 (if they were spent, they are gone);
- the daily prize: locked again; a gift card won that day and still unused is taken back,
  unless the parent keeps it for them;
- the week of tanks: worked out again (streaks/), that day's tank is no longer full. Only
  until the next week starts.

Each piece stays in its module; this one only puts them in order."""

from datetime import date

from app.children.repository import ChildrenRepository
from app.clock import Clock, app_day
from app.daily_prize.repository import PrizeSpinsRepository
from app.day_off.repository import DayOffsRepository
from app.errors import ConflictError, NotFoundError
from app.events.service import EventLog
from app.missions.repository import MissionsRepository
from app.settings import SettingsRepository
from app.stars.repository import StarsRepository
from app.streaks.service import StreaksService
from app.streaks.week import FULL
from app.today.plan import missions_by_day
from app.today.repository import DayRepository
from app.today.service import DayService


class UndoService:
    def __init__(
        self,
        children: ChildrenRepository,
        missions: MissionsRepository,
        days: DayRepository,
        day: DayService,
        stars: StarsRepository,
        spins: PrizeSpinsRepository,
        streaks: StreaksService,
        offs: DayOffsRepository,
        settings: SettingsRepository,
        clock: Clock,
        events: EventLog,
    ):
        self._children = children
        self._missions = missions
        self._days = days
        self._day = day
        self._stars = stars
        self._spins = spins
        self._streaks = streaks
        self._offs = offs
        self._settings = settings
        self._clock = clock
        self._events = events

    def done_this_week(self, child_id: str) -> list[dict]:
        """The missions the child completed this week, newest first: what can be undone."""
        child = self._children.require(child_id)
        names = {m.id: m for m in self._missions.list()}
        today = self._today()
        found = []
        for day, missions in self._days.completions(child.id).items():
            when = date.fromisoformat(day)
            if (today - when).days > 6 or not self._undoable(child.id, when):
                continue
            found += [{"day": when, "mission": names[m]} for m in sorted(missions) if m in names]
        return sorted(found, key=lambda d: d["day"], reverse=True)

    def preview(self, child_id: str, mission_id: str, day: date) -> dict:
        """What undoing it would take with it, for the window that asks."""
        child = self._children.require(child_id)
        stars = self._completion(child.id, mission_id, day)["stars"]
        cards = self._spins.spins_of(day, child.id)
        return {
            "mission": self._missions.get(mission_id),
            "day": day,
            "reopens": self._reopens(child.id, mission_id, day),
            "stars": min(stars, self._stars.balance(child.id)),
            "cards": [{"id": c["id"], "text": c["prize_text"], "used": bool(c["delivered_at"])} for c in cards],
            "tank": self._tank_empties(child.id, mission_id, day),
        }

    def undo(self, child_id: str, mission_id: str, day: date, keep_card: bool = False) -> dict:
        before = self.preview(child_id, mission_id, day)
        child = self._children.require(child_id)
        self._days.uncomplete(day, child, mission_id, before["stars"], self._clock.now())
        taken = []
        if not keep_card:
            for card in before["cards"]:
                if not card["used"]:
                    self._spins.remove(card["id"])
                    taken.append(card["text"])
        changes = {"gift": -before["stars"]} if before["stars"] else {}
        if taken:
            changes["card"] = ", ".join(taken)
        self._events.config_changed("mission", "undone", child=child, mission=before["mission"], changes=changes)
        return before

    # ---------- helpers ----------

    def _today(self) -> date:
        return app_day(self._clock.now(), self._settings.settings().day_starts_at)

    def _undoable(self, child_id: str, day: date) -> bool:
        try:
            self._streaks.undo_check(child_id, day)
        except ConflictError:
            return False
        return True

    def _completion(self, child_id: str, mission_id: str, day: date) -> dict:
        row = self._days.completion(day, child_id, mission_id)
        if row is None:
            raise NotFoundError("That mission was not done that day")
        self._streaks.undo_check(child_id, day)
        return row

    def _reopens(self, child_id: str, mission_id: str, day: date) -> bool:
        """Open again (today, inside its hours, or opened by a parent) or else closed, missed."""
        if day != self._today():
            return False
        item = next((m for m in self._day.today(child_id).missions if m.mission.id == mission_id), None)
        end = item and item.schedule and item.schedule.end
        opened = mission_id in self._days.opened_missions(day, child_id)
        return opened or not end or self._clock.now().strftime("%H:%M") < end

    def _tank_empties(self, child_id: str, mission_id: str, day: date) -> bool:
        """With rachas on, whether that day's full tank would no longer be full."""
        view = self._streaks.week(child_id)
        tank = view and next((t for t in view["week"].tanks if t.day == day), None)
        had = missions_by_day(self._missions.list(), child_id, self._offs.by_day(child_id))(day)
        return bool(tank and tank.state == FULL and mission_id in had)
