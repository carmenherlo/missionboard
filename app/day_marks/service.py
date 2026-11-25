"""La semana, misión a misión (semana-misiones.html, 25/11): in Padres · Niños a parent
picks a day of the racha's week and taps each mission to say what it was. A day gone by:
done → missed → free; today: pending → done → free; a day to come: active ↔ free (what has
not happened can only be let off). The stars follow the missions («Hecha» wins its star,
«No hecha» and «Libre» take it back, never below 0; the gift card stays: the wheel is the
child's) and the racha's day comes out of the sums (week.py: 100 % of the missions that
count). The first change to a day keeps a snapshot of how the app had left it, so
«Deshacer cambios» brings it back."""

from datetime import date, timedelta
from types import SimpleNamespace

from app.children.repository import ChildrenRepository
from app.clock import Clock
from app.day_marks.repository import DaySnapshotsRepository
from app.day_off.repository import WHOLE_DAY, DayOffsRepository
from app.errors import ConflictError, InvalidError, NotFoundError
from app.events.service import EventLog
from app.missions.repository import MissionsRepository
from app.settings import SettingsRepository
from app.streaks.service import StreaksService
from app.streaks.week import FREE, WEEKDAYS
from app.today.plan import missions_by_day
from app.today.repository import DayRepository
from app.undo.service import UndoService

DONE, MISSED, PENDING, ACTIVE = "done", "missed", "pending", "active"
CYCLES = {"past": (DONE, MISSED, FREE), "today": (PENDING, DONE, FREE), "later": (ACTIVE, FREE)}


class DayMarksService:
    def __init__(
        self,
        undo: UndoService,
        children: ChildrenRepository,
        missions: MissionsRepository,
        days: DayRepository,
        offs: DayOffsRepository,
        snapshots: DaySnapshotsRepository,
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
        self._snapshots = snapshots
        self._streaks = streaks
        self._settings = settings
        self._clock = clock
        self._events = events

    # ---------- reading ----------

    def week(self, child_id: str) -> list[dict] | None:
        """The days of the racha's week shown (the workshop's), with each tank's state; a day
        whose missions are all let off is still there, as free. None while rachas are off."""
        view = self._streaks.week(child_id)
        if view is None:
            return None
        week, rules = view["week"], self._settings.settings().streak_week
        tanks = {t.day: t.state for t in week.tanks}
        base, since = self._base(child_id), self._streaks.started(child_id)
        days = []
        for day in (week.start + timedelta(days=n) for n in range(7)):
            if day in tanks:
                days.append({"day": day, "state": tanks[day]})
            elif WEEKDAYS[day.weekday()] in rules.days and base(day) and day >= since:
                days.append({"day": day, "state": FREE})
        return days

    def day(self, child_id: str, day: date) -> dict:
        """Each mission of theirs that day and its state, and the sums."""
        child = self._children.require(child_id)
        kind = self._kind(day)
        off = self._offs.on(child.id, day)
        done = self._days.completions(child.id).get(day.isoformat(), set())
        missions = []
        for mission in self._their_missions(child.id, day):
            if WHOLE_DAY in off or mission.id in off:
                state = FREE
            elif mission.id in done:
                state = DONE
            else:
                state = {"past": MISSED, "today": PENDING, "later": ACTIVE}[kind]
            missions.append({"mission": mission, "state": state})
        counted = [m for m in missions if m["state"] != FREE]
        won = [m for m in counted if m["state"] == DONE]
        snapshot = self._snapshots.get(child.id, day)
        return {
            "day": day,
            "kind": kind,
            "editable": self._editable(child.id, day),
            "missions": missions,
            "done": len(won),
            "counted": len(counted),
            "stars": sum(self._stars_of(child.id, day, m["mission"].id) for m in won),
            "streak_day": _streak_day(kind, len(won), len(counted)),
            "changed": snapshot is not None,
            "reset_stars": self._reset_stars(child.id, day, snapshot, done) if snapshot else 0,
        }

    # ---------- changing ----------

    def set_state(self, child_id: str, day: date, mission_id: str, state: str) -> dict:
        child = self._children.require(child_id)
        kind = self._kind(day)
        if state not in CYCLES[kind]:
            raise InvalidError(f"On that day a mission can be: {', '.join(CYCLES[kind])}")
        if mission_id not in {m.id for m in self._their_missions(child.id, day)}:
            raise NotFoundError("That mission is not theirs that day")
        if kind != "later":
            self._streaks.undo_check(child.id, day)
            self._keep_snapshot(child.id, day)
        off = self._offs.on(child.id, day)
        phrase = next(iter(off.values()), "")
        if WHOLE_DAY in off:  # the whole day off becomes each of its missions off
            off = {m.id for m in self._their_missions(child.id, day)}
        off = set(off) - {WHOLE_DAY}
        was_off = mission_id in off
        off = off | {mission_id} if state == FREE else off - {mission_id}
        done = mission_id in self._days.completions(child.id).get(day.isoformat(), set())
        if done and state != DONE:
            self._undo.undo(child.id, mission_id, day, keep_card=True)
        elif state == DONE and not done:
            self._mark_done(child, day, mission_id)
        self._offs.replace(child.id, day, off, phrase if off else "", self._clock.now())
        if was_off != (state == FREE):
            self._log_off(child, day, mission_id, state == FREE)
        return self.day(child.id, day)

    def reset(self, child_id: str, day: date) -> dict:
        """The day as the app had left it, before any parent touched it."""
        child = self._children.require(child_id)
        snapshot = self._snapshots.get(child.id, day)
        if snapshot is None:
            return self.day(child.id, day)
        self._streaks.undo_check(child.id, day)
        done = self._days.completions(child.id).get(day.isoformat(), set())
        for mission_id in sorted(done - set(snapshot["done"])):
            self._undo.undo(child.id, mission_id, day, keep_card=True)
        now = self._clock.now()
        for mission_id, (stars, name) in snapshot["done"].items():
            if mission_id not in done:
                self._days.complete(day, child, SimpleNamespace(id=mission_id, name=name), stars, now)
        off = snapshot["off"]
        self._offs.replace(child.id, day, set(off), next(iter(off.values()), ""), now)
        self._snapshots.delete(child.id, day)
        self._events.config_changed("day", "reset", child=child, mission=_when(day))
        return self.day(child.id, day)

    # ---------- helpers ----------

    def _kind(self, day: date) -> str:
        today = self._streaks.today()
        return "past" if day < today else "today" if day == today else "later"

    def _editable(self, child_id: str, day: date) -> bool:
        if day > self._streaks.today():
            return True
        try:
            self._streaks.undo_check(child_id, day)
        except ConflictError:
            return False
        return True

    def _base(self, child_id: str):
        """had(day) without what is let off: every mission of theirs that day."""
        return missions_by_day(self._missions.list(), child_id)

    def _their_missions(self, child_id: str, day: date) -> list:
        had = self._base(child_id)(day)
        return [m for m in self._missions.list() if m.id in had]

    def _stars_of(self, child_id: str, day: date, mission_id: str) -> int:
        row = self._days.completion(day, child_id, mission_id)
        return row["stars"] if row else 0

    def _keep_snapshot(self, child_id: str, day: date) -> None:
        done = {}
        for mission_id in self._days.completions(child_id).get(day.isoformat(), set()):
            row = self._days.completion(day, child_id, mission_id)
            done[mission_id] = [row["stars"], row["mission_name"]]
        snapshot = {"done": done, "off": self._offs.on(child_id, day)}
        self._snapshots.keep_first(child_id, day, snapshot, self._clock.now())

    def _reset_stars(self, child_id: str, day: date, snapshot: dict, done: set[str]) -> int:
        """What «Deshacer cambios» would do to the stars (the question says it)."""
        back = sum(stars for m, (stars, _) in snapshot["done"].items() if m not in done)
        lost = sum(self._stars_of(child_id, day, m) for m in done - set(snapshot["done"]))
        return back - lost

    def _mark_done(self, child, day: date, mission_id: str) -> None:
        mission = self._missions.get(mission_id)
        stars = self._settings.settings().stars_per_mission
        if self._days.complete(day, child, mission, stars, self._clock.now()):
            changes = {"gift": stars, "day": _when(day).name}
            self._events.config_changed("mission", "marked_done", child=child, mission=mission, changes=changes)

    def _log_off(self, child, day: date, mission_id: str, on: bool) -> None:
        mission = self._missions.get(mission_id)
        self._events.config_changed(
            "mission_off", "on" if on else "off", child=child, mission=mission, changes={"day": _when(day).name}
        )


def _when(day: date) -> SimpleNamespace:
    return SimpleNamespace(id=day.isoformat(), name=f"{day.day}/{day.month}")


def _streak_day(kind: str, done: int, counted: int) -> str:
    """won · lost · waiting (today, not yet, or a day to come) · free (nothing counts)."""
    if not counted:
        return FREE
    if done == counted:
        return "won"
    return "lost" if kind == "past" else "waiting"
