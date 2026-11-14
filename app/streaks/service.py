"""Rachas: the days in a row (count.py) and the week of fuel tanks (week.py, rachas.html
and taller.html): settling each week with its prize, the days let off, the fuel loaded
into the rocket and the parents handing the week's prize over."""

from datetime import date, timedelta
from types import SimpleNamespace

from app.children.repository import Child, ChildrenRepository
from app.clock import Clock, app_day
from app.errors import NotFoundError
from app.events.service import EventLog
from app.missions.repository import MissionsRepository
from app.settings import SettingsRepository
from app.streaks.count import streak
from app.streaks.repository import StreaksRepository
from app.streaks.week import FULL, Week, build_week, week_end
from app.today.plan import missions_by_day
from app.today.repository import DayRepository


class StreaksService:
    def __init__(
        self,
        children: ChildrenRepository,
        missions: MissionsRepository,
        days: DayRepository,  # which missions each child completed, each day
        streaks: StreaksRepository,
        settings: SettingsRepository,
        clock: Clock,
        events: EventLog,
    ):
        self._children = children
        self._missions = missions
        self._days = days
        self._streaks = streaks
        self._settings = settings
        self._clock = clock
        self._events = events

    def streak(self, child_id: str, day: date | None = None) -> int:
        """Days in a row with their missions done (count.py)."""
        settings = self._settings.settings()
        day = day or app_day(self._clock.now(), settings.day_starts_at)
        had = missions_by_day(self._missions.list(), child_id)
        return streak(day, settings.streak_rule, had, self._days.completions(child_id))

    def week(self, child_id: str) -> dict | None:
        """This week's tanks and the result of a week the child has not seen yet (once
        it is closed, it is kept, with its prize). None while rachas are off."""
        if not self._settings.features().streaks:
            return None
        child = self._children.require(child_id)
        settings = self._settings.settings()
        rules = settings.streak_week
        today = app_day(self._clock.now(), settings.day_starts_at)
        had = missions_by_day(self._missions.list(), child.id)
        done, free = self._days.completions(child.id), self._streaks.free_days(child.id)
        end = week_end(today, rules.prize_day)
        settled = self._streaks.weeks(child.id)
        current = build_week(today, end, rules, settings.streak_rule, had, done, free)
        previous_end = end - timedelta(days=7)
        if not settled:  # the first time: the weeks before rachas existed are not judged
            now = self._clock.now()
            self._streaks.settle_week(child, previous_end, "none", "", 0, 0, now)
            self._streaks.week_seen(child.id, previous_end.isoformat(), now)
        else:  # a week can close while nobody looks (Friday missed): settled on the next look
            previous = build_week(today, previous_end, rules, settings.streak_rule, had, done, free)
            self._settle(child, previous, rules, settled)
        self._settle(child, current, rules, settled)
        settled = self._streaks.weeks(child.id)
        unseen = [
            row
            for row in settled.values()
            if row["shown_at"] is None and row["week_end"] >= (end - timedelta(days=7)).isoformat()
        ]
        result = max(unseen, key=lambda row: row["week_end"]) if unseen else None
        # The week whose rocket takes off (taller.html): this one, or the one before if
        # it closed while nobody looked (Saturday, a new week already).
        launch = None
        if result:
            result_end = date.fromisoformat(result["week_end"])
            launch = (
                current
                if result_end == end
                else build_week(today, result_end, rules, settings.streak_rule, had, done, free)
            )
        return {"week": current, "result": result, "launch": launch, "loaded": self._streaks.fuel_loads(child.id)}

    def load_fuel(self, child_id: str, day: date) -> dict | None:
        """The child loads a full tank into the rocket (taller.html): one of this week, or
        of the week whose rocket is still to take off."""
        view = self.week(child_id)
        if view is None:
            raise NotFoundError("Rachas are off")
        weeks = [view["week"]] + ([view["launch"]] if view["launch"] else [])
        tank = next((t for w in weeks for t in w.tanks if t.day == day), None)
        if tank is None or tank.state != FULL:
            raise NotFoundError("No full tank that day")
        child = self._children.require(child_id)
        if self._streaks.load_fuel(child.id, day, self._clock.now()):
            self._events.child_did("fuel_loaded", child, prize=day.isoformat())
            view["loaded"].add(day.isoformat())
        return view

    def _settle(self, child: Child, week: Week, rules, settled: dict) -> None:
        if not week.closed or not week.counted or week.end.isoformat() in settled:
            return
        tier = week.tier(rules)
        text = {"full": rules.prize, "second": rules.second}.get(tier, "")
        image = {"full": rules.prize_image, "second": rules.second_image}.get(tier)
        self._streaks.settle_week(child, week.end, tier, text, week.full, week.counted, self._clock.now(), image)
        self._events.child_did(f"week_{tier}", child, prize=f"{week.full} de {week.counted}")

    def week_seen(self, child_id: str, end: str) -> None:
        self._streaks.week_seen(self._children.require(child_id).id, end, self._clock.now())

    def set_free_day(self, child_id: str, day: date, free: bool) -> None:
        child = self._children.require(child_id)
        self._streaks.set_free_day(child.id, day, free, self._clock.now())
        self._events.config_changed(
            "free_day",
            "on" if free else "off",
            child=child,
            mission=SimpleNamespace(id=day.isoformat(), name=f"{day.day}/{day.month}"),
        )

    def prizes_to_give(self) -> list[dict]:
        return self._streaks.week_prizes_to_give()

    def deliver_week_prize(self, child_id: str, end: str) -> None:
        row = self._streaks.weeks(child_id).get(end)
        if row is None or row["tier"] == "none":
            raise NotFoundError("Prize not found")
        if self._streaks.deliver_week_prize(child_id, end, self._clock.now()):
            self._events.config_changed(
                "week_prize",
                "delivered",
                child=SimpleNamespace(id=row["child_id"], name=row["child_name"]),
                mission=SimpleNamespace(id=end, name=row["prize_text"] or "premio sorpresa"),
            )
