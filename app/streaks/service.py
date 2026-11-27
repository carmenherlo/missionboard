"""Rachas (20/11): the one place that answers about a child's week. The
week and its result are worked out each time from the missions done and the days let off
(week.py); nothing is "settled" when a week closes, so a parent can change any day of it
(undo/, day_off/) and the week simply comes out different. What is stored is only what
happened: the child launched the rocket (or heard it cough), the fuel they loaded, the
prize handed over, and a week's final result once it is over (the next one has started)."""

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
from app.streaks.week import FULL, WEEKDAYS, Week, build_week, next_start, shown_end, week_end
from app.today.plan import missions_by_day, whole_days_off
from app.today.repository import DayRepository

MAX_WEEKS_BACK = 60  # how far back weeks are looked for to freeze (a tablet off for months)


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

    def today(self) -> date:
        return app_day(self._clock.now())

    def streak(self, child_id: str, day: date | None = None) -> int:
        """Days in a row with all their missions done (count.py)."""
        day = day or self.today()
        offs = self._offs.by_day(child_id)
        had, free = missions_by_day(self._missions.list(), child_id, offs), whole_days_off(offs)
        # A day let off neither counts nor breaks it, as a day without missions.
        return streak(day, lambda d: set() if d.isoformat() in free else had(d), self._days.completions(child_id))

    def started(self, child_id: str) -> date:
        """The day the child's racha started: the days before it are not judged."""
        return self._streaks.start(child_id, self.today())

    # ---------- the week the child and the parents see ----------

    def week(self, child_id: str) -> dict | None:
        """The week to show (this one, or the one just closed until the next starts), its
        result if the child has not seen it yet, and whether its rocket took off. None while
        rachas are off."""
        if not self._settings.features().streaks:
            return None
        child = self._children.require(child_id)
        rules, today, build = self._builder(child.id)
        self._freeze_over(child, today, build)
        end = shown_end(today, rules, lambda e: build(e).counted > 0)
        week = build(end)
        row = self._streaks.weeks(child.id).get(end.isoformat()) or {}
        tier = week.tier(rules) if week.closed else None
        launched = row.get("launched_tier")
        # New for the child: not seen yet, or different from what they saw (a parent changed a
        # day, 20/11): the workshop always shows the week as it is now.
        new = tier is not None and launched != tier
        loads = self._streaks.fuel_loads(child.id)
        return {
            "week": week,
            "result": self._result(week, tier) if new else None,
            "took_off": launched in ("full", "second") and launched == tier,
            "loaded": {t.day.isoformat() for t in week.tanks if t.state == FULL and t.day.isoformat() in loads},
            "today": today,
            "next_day": _next_day(today, rules.days),
        }

    def load_fuel(self, child_id: str, day: date) -> dict | None:
        """The child loads a full tank of the week shown into the rocket (taller.html)."""
        view = self.week(child_id)
        if view is None:
            raise NotFoundError("Rachas are off")
        tank = next((t for t in view["week"].tanks if t.day == day), None)
        if tank is None or tank.state != FULL:
            raise NotFoundError("No full tank that day")
        child = self._children.require(child_id)
        if self._streaks.load_fuel(child.id, day, self._clock.now()):
            self._events.child_did("fuel_loaded", child, prize=day.isoformat())
            view["loaded"].add(day.isoformat())
        return view

    def week_seen(self, child_id: str, end: str) -> None:
        """The child pulled the lever (the rocket took off) or heard it cough: they have
        seen how the week shown ended, and with which prize."""
        view = self.week(child_id)
        result = view and view["result"]
        if not result or result["week_end"] != end:
            return
        child = self._children.require(child_id)
        tier = result["tier"]
        self._streaks.launched(child, end, tier, result["prize_text"], result["prize_image"], self._clock.now())
        self._events.child_did(f"week_{tier}", child, prize=f"{result['full_days']} de {result['days']}")

    # ---------- the parents ----------

    def undo_check(self, child_id: str, day: date) -> None:
        """Before changing a day gone by (undo/, day_marks/): its week can be changed until the
        next one starts, its first day that counts (with Monday to Friday, until Monday), even
        if its rocket took off. A day to come is only let off."""
        rules, today = self._settings.settings().streak_week, self.today()
        if day > today:
            raise ConflictError("A day to come cannot be done or undone")
        if today >= next_start(week_end(day, rules.prize_day), rules):
            raise ConflictError("That week is over: the next one has started")

    def set_free_day(self, child_id: str, day: date, free: bool) -> None:
        """The whole day off, or not (Padres · Niño, the week's tanks): the missions let off
        that day stay as they are. The week comes out with one tank fewer (or more)."""
        child = self._children.require(child_id)
        off = self._offs.on(child.id, day)
        if free:
            self._offs.replace(child.id, day, {*off, WHOLE_DAY}, next(iter(off.values()), ""), self._clock.now())
        else:
            self._offs.remove(child.id, day, WHOLE_DAY)
        self._events.config_changed(
            "free_day",
            "on" if free else "off",
            child=child,
            mission=SimpleNamespace(id=day.isoformat(), name=f"{day.day}/{day.month}"),
        )

    def prizes_to_give(self) -> list[dict]:
        """The prizes of a week won and not handed over yet, oldest first: the week shown of
        each child (as it is now) and the weeks over (as they ended)."""
        found = {}
        if self._settings.features().streaks:
            for child in self._children.list():
                found.update(self._live_prize(child))
        for row in self._streaks.all_weeks():
            if row["frozen_at"] and row["tier"] not in (None, "none") and not row["delivered_at"]:
                found[(row["child_id"], row["week_end"])] = row
        return sorted(found.values(), key=lambda row: (row["week_end"], row["child_name"]))

    def deliver_week_prize(self, child_id: str, end: str) -> None:
        child = self._children.require(child_id)
        prize = self._live_prize(child).get((child.id, end)) or self._streaks.weeks(child.id).get(end)
        if not prize or prize.get("tier") in (None, "none"):
            raise NotFoundError("Prize not found")
        if self._streaks.deliver(child, end, self._clock.now()):
            self._events.config_changed(
                "week_prize",
                "delivered",
                child=child,
                mission=SimpleNamespace(id=end, name=prize["prize_text"] or "premio sorpresa"),
            )

    def undeliver_week_prize(self, child_id: str, end: str) -> None:
        self._streaks.undeliver_week_prize(child_id, end)

    # ---------- helpers ----------

    def _builder(self, child_id: str):
        """The rules, today, and build(end): the week ending then, as it is today."""
        settings = self._settings.settings()
        today = app_day(self._clock.now())
        since = self._streaks.start(child_id, today)
        offs = self._offs.by_day(child_id)
        had = missions_by_day(self._missions.list(), child_id, offs)
        done, free = self._days.completions(child_id), whole_days_off(offs)
        rules = settings.streak_week
        return rules, today, lambda end: build_week(today, end, rules, had, done, free, since)

    def _result(self, week: Week, tier: str) -> dict:
        """A closed week's result, with the prize of its tier as the parents set it now."""
        rules = self._settings.settings().streak_week
        return {
            "week_end": week.end.isoformat(),
            "tier": tier,
            "prize_text": {"full": rules.prize, "second": rules.second}.get(tier, ""),
            "prize_image": {"full": rules.prize_image, "second": rules.second_image}.get(tier),
            "full_days": week.full,
            "days": week.counted,
        }

    def _live_prize(self, child: Child) -> dict:
        """The week shown, if closed with a prize not handed over: {(child, end): prize}."""
        view = self.week(child.id)
        week = view and view["week"]
        if not week or not week.closed:
            return {}
        rules = self._settings.settings().streak_week
        tier = week.tier(rules)
        row = self._streaks.weeks(child.id).get(week.end.isoformat()) or {}
        if tier == "none" or row.get("delivered_at"):
            return {}
        prize = self._result(week, tier)
        if row.get("launched_tier") == tier:  # what the child saw when the rocket landed
            prize["prize_text"] = row["prize_text"]
        return {(child.id, prize["week_end"]): {**prize, "child_id": child.id, "child_name": child.name}}

    def _freeze_over(self, child: Child, today: date, build) -> None:
        """Weeks over (the next one has started) keep their final result, as they ended."""
        rules = self._settings.settings().streak_week
        rows = self._streaks.weeks(child.id)
        frozen = [end for end, row in rows.items() if row["frozen_at"]]
        first = self._streaks.start(child.id, today)
        if frozen:
            first = max(first, date.fromisoformat(max(frozen)) + timedelta(days=1))
        end = week_end(max(first, today - timedelta(weeks=MAX_WEEKS_BACK)), rules.prize_day)
        while next_start(end, rules) <= today:
            row = rows.get(end.isoformat()) or {}
            week = build(end)
            if not row.get("frozen_at") and (week.counted or row):
                tier = week.tier(rules) if week.closed else "none"
                prize = self._result(week, tier)
                if row.get("launched_tier") == tier:  # what the child saw when the rocket landed
                    prize.update(prize_text=row["prize_text"], prize_image=row["prize_image"])
                self._streaks.freeze(
                    child, end.isoformat(), tier, week.full, week.counted, prize["prize_text"], prize["prize_image"],
                    self._clock.now(),
                )  # fmt: skip
            end += timedelta(days=7)


def _next_day(today: date, days) -> date:
    """The next day that counts, after today (the workshop rests till then)."""
    day = today + timedelta(days=1)
    while WEEKDAYS[day.weekday()] not in days:
        day += timedelta(days=1)
    return day
