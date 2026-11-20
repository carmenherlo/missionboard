"""Rachas: the days in a row (count.py) and the week of fuel tanks (week.py, rachas.html
and taller.html): settling each week with its prize, the days let off, the fuel loaded
into the rocket and the parents handing the week's prize over."""

from datetime import date, timedelta
from types import SimpleNamespace

from app.children.repository import Child, ChildrenRepository
from app.clock import Clock, app_day
from app.day_off.repository import WHOLE_DAY, DayOffsRepository
from app.errors import ConflictError, NotFoundError
from app.events.service import EventLog
from app.missions.repository import MissionsRepository
from app.settings import SettingsRepository
from app.streaks.count import streak
from app.streaks.repository import StreaksRepository
from app.streaks.week import FULL, WEEKDAYS, Week, build_week, week_end
from app.today.plan import missions_by_day, whole_days_off
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
        offs: DayOffsRepository,  # the days and missions let off (day_off/)
    ):
        self._offs = offs
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
        offs = self._offs.by_day(child_id)
        had, free = missions_by_day(self._missions.list(), child_id, offs), whole_days_off(offs)
        # A day let off neither counts nor breaks it, as a day without missions.
        return streak(
            day,
            settings.streak_rule,
            lambda d: set() if d.isoformat() in free else had(d),
            self._days.completions(child_id),
        )

    def week(self, child_id: str) -> dict | None:
        """This week's tanks and the result of a week the child has not seen yet (once
        it is closed, it is kept, with its prize). None while rachas are off."""
        if not self._settings.features().streaks:
            return None
        child = self._children.require(child_id)
        rules, today, build = self._builder(child.id)
        end = week_end(today, rules.prize_day)
        settled = self._streaks.weeks(child.id)
        current = build(end)
        previous_end = end - timedelta(days=7)
        if not settled:  # the first time: the weeks before rachas existed are not judged
            now = self._clock.now()
            self._streaks.settle_week(child, previous_end, "none", "", 0, 0, now)
            self._streaks.week_seen(child.id, previous_end.isoformat(), now)
        else:  # a week can close while nobody looks (Friday missed): settled on the next look
            self._settle(child, build(previous_end), rules, settled)
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
            launch = current if result_end == end else build(result_end)
        row = settled.get(end.isoformat())
        return {
            "week": current,
            # This week's rocket took off already (20/11): the workshop has no rocket till the next.
            "took_off": bool(row and row["tier"] != "none" and row["shown_at"]),
            "result": result,
            "launch": launch,
            "loaded": self._streaks.fuel_loads(child.id),
            "today": today,
        }

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

    def _builder(self, child_id: str):
        """The rules, today, and build(end): the week ending then, as it is today."""
        settings = self._settings.settings()
        today = app_day(self._clock.now(), settings.day_starts_at)
        offs = self._offs.by_day(child_id)
        had = missions_by_day(self._missions.list(), child_id, offs)
        done, free = self._days.completions(child_id), whole_days_off(offs)
        rules = settings.streak_week
        return rules, today, lambda end: build_week(today, end, rules, settings.streak_rule, had, done, free)

    def _settle(self, child: Child, week: Week, rules, settled: dict, before: str | None = None) -> None:
        """Keep a closed week's result. before: its tier until a day changed (logged only if it moves)."""
        if not week.closed or not week.counted or week.end.isoformat() in settled:
            return
        tier = week.tier(rules)
        text = {"full": rules.prize, "second": rules.second}.get(tier, "")
        image = {"full": rules.prize_image, "second": rules.second_image}.get(tier)
        self._streaks.settle_week(child, week.end, tier, text, week.full, week.counted, self._clock.now(), image)
        if tier != before:
            self._events.child_did(f"week_{tier}", child, prize=f"{week.full} de {week.counted}")

    def week_seen(self, child_id: str, end: str) -> None:
        self._streaks.week_seen(self._children.require(child_id).id, end, self._clock.now())

    def set_free_day(self, child_id: str, day: date, free: bool) -> None:
        """The whole day off, or not (Padres · Niño, the week's tanks): the missions let off
        that day stay as they are."""
        child = self._children.require(child_id)
        off = self._offs.on(child.id, day)
        if free:
            self._offs.replace(child.id, day, {*off, WHOLE_DAY}, next(iter(off.values()), ""), self._clock.now())
        else:
            self._offs.remove(child.id, day, WHOLE_DAY)
        self.after_change(child.id, day)  # 20/11: with fewer (or more) days, the week is settled again
        self._events.config_changed(
            "free_day",
            "on" if free else "off",
            child=child,
            mission=SimpleNamespace(id=day.isoformat(), name=f"{day.day}/{day.month}"),
        )

    def today(self) -> date:
        return app_day(self._clock.now(), self._settings.settings().day_starts_at)

    def undo_check(self, child_id: str, day: date) -> None:
        """Before changing a day gone by (undo/): its week can be changed until the next one
        starts, its first day that counts (20/11: with Monday to Friday, until Monday), even
        if its rocket took off. A day to come is only let off."""
        settings = self._settings.settings()
        today = app_day(self._clock.now(), settings.day_starts_at)
        if day > today:
            raise ConflictError("A day to come cannot be done or undone")
        if today >= _next_start(week_end(day, settings.streak_week.prize_day), settings.streak_week.days):
            raise ConflictError("That week is over: the next one has started")

    def after_change(self, child_id: str, day: date) -> None:
        """A day changed (a mission undone or marked done, the day let off or back): its week
        is settled again. If its rocket took off already, it only takes off again for a
        better prize; a prize handed over stays handed over. If that day's tank is no longer
        full, its fuel goes back out of the rocket."""
        if not self._settings.features().streaks:
            return
        child = self._children.require(child_id)
        rules, _, build = self._builder(child.id)
        week = build(week_end(day, rules.prize_day))
        end = week.end.isoformat()
        old = self._streaks.weeks(child.id).get(end)
        self._streaks.forget_week(child.id, end)
        self._settle(child, week, rules, {}, before=old and old["tier"])
        new = self._streaks.weeks(child.id).get(end)
        if old and new:
            shown = old["shown_at"] if RANK[new["tier"]] <= RANK[old["tier"]] else None
            self._streaks.restore_week(child.id, end, shown, old["delivered_at"] if new["tier"] != "none" else None)
        tank = next((t for t in week.tanks if t.day == day), None)
        if not tank or tank.state != FULL:
            self._streaks.unload_fuel(child.id, day)

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


RANK = {"none": 0, "second": 1, "full": 2}


def _next_start(end: date, days) -> date:
    """The first day that counts after a week's end: the next week has started."""
    day = end + timedelta(days=1)
    while WEEKDAYS[day.weekday()] not in days:
        day += timedelta(days=1)
    return day
