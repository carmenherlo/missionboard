"""A child's day: which missions they have today, in which state, and what
happens when they check a step. The rules are here; the screens only show them.

States of a mission today (paso-4.html, "Las reglas del día"):
- done: everything the child checks, checked today. It stays done until tomorrow.
- open: no schedule, or inside it, or opened by a parent for today (it counts for
  its star and the prize). Things can be checked and unchecked.
- upcoming: before its start time. It cannot be opened yet.
- closed: past its end time without being done. No star.
Which hours count: for a child who follows the mission's routine, on the routine's
days, the routine's; for everyone else, and on other days, the mission's.
The focus (the big one on the route) is the first open mission in route
order ("¡Ahora!"); if none is open, the next upcoming one, with its time.

The daily prize (paso-5.html) waits at the end of the route: locked until
every mission of today is done (a closed one means no prize today), then
unlocked for settings.daily_prize_spins spins, then won (showing what it was).
"""

import secrets

from dataclasses import dataclass, field
from datetime import date, timedelta
from types import SimpleNamespace

from app.children.repository import Child, ChildrenRepository
from app.clock import Clock, app_day
from app.errors import ConflictError, InvalidError, NotFoundError
from app.events.service import EventLog
from app.missions.repository import WEEKDAYS, ChildTask, Mission, MissionsRepository, Schedule, child_tasks
from app.prizes.repository import Prize, PrizesRepository
from app.routines import links
from app.routines.repository import RoutinesRepository, minute_of
from app.settings import MOMENTS, Season, SettingsRepository
from app.today.repository import DayRepository
from app.today.streaks import streak
from app.today.week import FULL, Week, build_week, week_end

DONE, OPEN, UPCOMING, CLOSED = "done", "open", "upcoming", "closed"
LOCKED, UNLOCKED, WON = "locked", "unlocked", "won"

# What a child can do on the route that only goes to the event log.
NOTES = ("mission_opened", "step_spoken", "mission_locked", "prize_locked")


@dataclass
class MissionToday:
    mission: Mission
    state: str
    tasks: list[ChildTask]  # what this child has of it today
    checked: set[str] = field(default_factory=set)  # what they have checked, of `marks`
    focus: bool = False
    schedule: Schedule | None = None  # the hours that count for them today

    @property
    def marks(self) -> list[str]:
        return [mark for task in self.tasks for mark in task.marks]

    def item(self, item_id: str):
        """A task or step this child has today."""
        for task in self.tasks:
            if task.task.id == item_id:
                return task.task
            for step in task.steps:
                if step.id == item_id:
                    return step
        return None


@dataclass
class PrizeToday:
    state: str
    prizes: list[Prize]  # the wheel
    won: list[dict]  # what came out today: {"prize_id", "text", "image"}
    spins_left: int


@dataclass
class Today:
    child: Child
    day: date
    season: Season
    moment: str  # manana, dia, tarde or noche
    missions: list[MissionToday]
    stars: int
    prize: PrizeToday | None = None  # None: no prize at the end of the route
    streak: int | None = None  # days in a row (step 8); None: rachas switched off

    @property
    def focus_is_now(self) -> bool:
        return any(m.focus and m.state == OPEN for m in self.missions)


@dataclass
class StepResult:
    today: Today
    completed: bool  # this check completed the mission
    stars_earned: int


@dataclass
class SpinResult:
    today: Today
    prize: Prize


def _checked_tasks(tasks: list[ChildTask], checked: set[str]) -> set[str]:
    """The tasks checked today. Before misiones-3 a child checked steps: a task whose
    steps were all checked that day counts as checked too, so nobody loses it."""
    return {
        task.task.id for task in tasks
        if task.task.id in checked or (task.steps and all(s.id in checked for s in task.steps))
    }


def current_season(seasons: tuple[Season, ...], day: date) -> Season:
    """The last one that has started; in January, the last of the list goes on."""
    started = [season for season in seasons if season.start <= day.strftime("%m-%d")]
    return started[-1] if started else seasons[-1]


def current_moment(season: Season, time: str) -> str:
    """The last moment that has started; before the morning, the night goes on."""
    started = [moment for moment in MOMENTS if getattr(season, moment) <= time]
    return started[-1] if started else "noche"


class DayService:
    def __init__(
        self,
        children: ChildrenRepository,
        missions: MissionsRepository,
        days: DayRepository,
        settings: SettingsRepository,
        clock: Clock,
        events: EventLog,
        prizes: PrizesRepository,
        routines: RoutinesRepository,
        choose=secrets.choice,  # tests pass their own, to know the prize
    ):
        self._children = children
        self._missions = missions
        self._days = days
        self._settings = settings
        self._clock = clock
        self._events = events
        self._prizes = prizes
        self._routines = routines
        self._choose = choose

    def today(self, child_id: str) -> Today:
        child = self._child(child_id)
        settings = self._settings.settings()
        now = self._clock.now()
        day = app_day(now, settings.day_starts_at)
        time = now.strftime("%H:%M")
        weekday = WEEKDAYS[day.weekday()]

        checked = self._days.checked_steps(day, child.id)
        completed = self._days.completed_missions(day, child.id)
        opened = self._days.opened_missions(day, child.id)
        routines = links.routine_by_mission(self._routines.list())
        missions = []
        for mission in self._missions.list():
            tasks = child_tasks(mission, child.id, weekday)
            if not tasks:  # not today, nothing of theirs today, or still being written
                continue
            schedule = links.schedule_on(mission, routines.get(mission.id), child.id, weekday)
            item = MissionToday(mission, self._state(schedule, mission.id in completed, mission.id in opened, time),
                                tasks, schedule=schedule)
            item.checked = _checked_tasks(tasks, checked.get(mission.id, set()))
            missions.append(item)

        focus = next((m for m in missions if m.state == OPEN), None)
        focus = focus or next((m for m in missions if m.state == UPCOMING), None)
        if focus:
            focus.focus = True
        return Today(
            child=child,
            day=day,
            season=(season := current_season(settings.seasons, day)),
            moment=current_moment(season, time),
            missions=missions,
            stars=self._days.stars(child.id),
            prize=self._prize_today(day, child, missions),
            streak=self.streak(child.id, day) if self._settings.features().streaks else None,
        )

    def streak(self, child_id: str, day: date | None = None) -> int:
        """Days in a row with their missions done (streaks.py)."""
        settings = self._settings.settings()
        day = day or app_day(self._clock.now(), settings.day_starts_at)
        missions = self._missions.list()
        by_weekday = {
            weekday: {m.id for m in missions if child_tasks(m, child_id, weekday)} for weekday in WEEKDAYS
        }
        return streak(day, settings.streak_rule, lambda d: by_weekday[WEEKDAYS[d.weekday()]],
                      self._days.completions(child_id))

    # ---------- rachas: the week of fuel tanks (rachas.html) ----------

    def week(self, child_id: str) -> dict | None:
        """This week's tanks and the result of a week the child has not seen yet (once
        it is closed, it is kept, with its prize). None while rachas are off."""
        if not self._settings.features().streaks:
            return None
        child = self._child(child_id)
        settings = self._settings.settings()
        rules = settings.streak_week
        today = app_day(self._clock.now(), settings.day_starts_at)
        missions = self._missions.list()
        by_weekday = {wd: {m.id for m in missions if child_tasks(m, child.id, wd)} for wd in WEEKDAYS}
        had = lambda d: by_weekday[WEEKDAYS[d.weekday()]]  # noqa: E731
        done, free = self._days.completions(child.id), self._days.free_days(child.id)
        end = week_end(today, rules.prize_day)
        settled = self._days.weeks(child.id)
        current = build_week(today, end, rules, settings.streak_rule, had, done, free)
        previous_end = end - timedelta(days=7)
        if not settled:  # the first time: the weeks before rachas existed are not judged
            now = self._clock.now()
            self._days.settle_week(child, previous_end, "none", "", 0, 0, now)
            self._days.week_seen(child.id, previous_end.isoformat(), now)
        else:  # a week can close while nobody looks (Friday missed): settled on the next look
            previous = build_week(today, previous_end, rules, settings.streak_rule, had, done, free)
            self._settle(child, previous, rules, settled)
        self._settle(child, current, rules, settled)
        settled = self._days.weeks(child.id)
        unseen = [row for row in settled.values()
                  if row["shown_at"] is None and row["week_end"] >= (end - timedelta(days=7)).isoformat()]
        result = max(unseen, key=lambda row: row["week_end"]) if unseen else None
        # The week whose rocket takes off (taller.html): this one, or the one before if
        # it closed while nobody looked (Saturday, a new week already).
        launch = None
        if result:
            result_end = date.fromisoformat(result["week_end"])
            launch = current if result_end == end else build_week(
                today, result_end, rules, settings.streak_rule, had, done, free)
        return {"week": current, "result": result, "launch": launch, "loaded": self._days.fuel_loads(child.id)}

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
        child = self._child(child_id)
        if self._days.load_fuel(child.id, day, self._clock.now()):
            self._events.child_did("fuel_loaded", child, prize=day.isoformat())
            view["loaded"].add(day.isoformat())
        return view

    def _settle(self, child: Child, week: Week, rules, settled: dict) -> None:
        if not week.closed or not week.counted or week.end.isoformat() in settled:
            return
        tier = week.tier(rules)
        text = {"full": rules.prize, "second": rules.second}.get(tier, "")
        image = {"full": rules.prize_image, "second": rules.second_image}.get(tier)
        self._days.settle_week(child, week.end, tier, text, week.full, week.counted, self._clock.now(), image)
        self._events.child_did(f"week_{tier}", child, prize=f"{week.full} de {week.counted}")

    def week_seen(self, child_id: str, end: str) -> None:
        self._days.week_seen(self._child(child_id).id, end, self._clock.now())

    def set_free_day(self, child_id: str, day: date, free: bool) -> None:
        child = self._child(child_id)
        self._days.set_free_day(child.id, day, free, self._clock.now())
        self._events.config_changed("free_day", "on" if free else "off", child=child,
                                    mission=SimpleNamespace(id=day.isoformat(), name=f"{day.day}/{day.month}"))

    def deliver_week_prize(self, child_id: str, end: str) -> None:
        row = self._days.weeks(child_id).get(end)
        if row is None or row["tier"] == "none":
            raise NotFoundError("Prize not found")
        if self._days.deliver_week_prize(child_id, end, self._clock.now()):
            self._events.config_changed(
                "week_prize", "delivered", child=SimpleNamespace(id=row["child_id"], name=row["child_name"]),
                mission=SimpleNamespace(id=end, name=row["prize_text"] or "premio sorpresa"))

    def _prize_today(self, day: date, child: Child, missions: list[MissionToday]) -> PrizeToday | None:
        spins = self._settings.settings().daily_prize_spins
        prizes = self._prizes.list()
        if not self._settings.features().daily_prize or not prizes or not missions or spins == 0:
            return None
        won = self._days.prize_spins(day, child.id)
        spins_left = max(0, spins - len(won))
        if not all(m.state == DONE for m in missions):
            state = LOCKED
        else:
            state = UNLOCKED if spins_left else WON
        return PrizeToday(state=state, prizes=prizes, won=won, spins_left=spins_left)

    def spin(self, child_id: str) -> SpinResult:
        """Spin the wheel: the prize is chosen and kept here; the screen only shows it."""
        today = self.today(child_id)
        if today.prize is None or today.prize.state != UNLOCKED:
            raise ConflictError("The prize is not unlocked")
        prize = self._choose(today.prize.prizes)
        self._days.add_prize_spin(today.day, today.child, prize, self._clock.now())
        self._events.child_did("prize_spun", today.child, prize=prize.text)
        return SpinResult(self.today(child_id), prize)

    def set_mark(self, child_id: str, mission_id: str, item_id: str, checked: bool) -> StepResult:
        """Check or uncheck a task (its steps are only reminders). The last one completes
        the mission (once a day)."""
        today = self.today(child_id)
        item = self._mission_today(today, mission_id)
        target = item.item(item_id)
        if target is None or item_id not in item.marks:
            raise NotFoundError("Nothing to check with that id")
        if item.state == DONE:
            if not checked:
                raise ConflictError("The mission is already done today")
            return StepResult(today, completed=False, stars_earned=0)
        if item.state != OPEN:
            raise ConflictError("The mission is not open now")
        if (item_id in item.checked) == checked:
            return StepResult(today, completed=False, stars_earned=0)

        now = self._clock.now()
        self._days.set_step(today.day, today.child.id, mission_id, item_id, checked, now)
        if not checked:  # steps checked before misiones-3 must not keep it checked
            for step in next(t for t in item.tasks if t.task.id == item_id).steps:
                self._days.set_step(today.day, today.child.id, mission_id, step.id, False, now)
        self._events.child_did(
            "step_checked" if checked else "step_unchecked", today.child, mission=item.mission, step=target
        )

        all_checked = (item.checked | {item_id}) >= set(item.marks)
        stars = 0
        if checked and all_checked:
            stars = self._settings.settings().stars_per_mission
            if self._days.complete(today.day, today.child, item.mission, stars, now):
                self._events.child_did("mission_completed", today.child, mission=item.mission, stars=stars)
            else:
                stars = 0
        after = self.today(child_id)
        if after.prize and after.prize.state == UNLOCKED and (today.prize is None or today.prize.state == LOCKED):
            self._events.child_did("prize_unlocked", today.child)
        return StepResult(after, completed=checked and all_checked, stars_earned=stars)

    def open_today(self, child_id: str, mission_id: str) -> Today:
        """A parent opens a closed or upcoming mission for this child, only today: it
        can be done and gives its star. It goes to the log; the child sees no option."""
        today = self.today(child_id)
        item = self._mission_today(today, mission_id)
        if item.state in (UPCOMING, CLOSED):
            self._days.open_mission(today.day, today.child.id, mission_id, self._clock.now())
            self._events.config_changed("mission", "opened_today", child=today.child, mission=item.mission)
        return self.today(child_id)

    def stars(self, child_id: str) -> int:
        return self._days.stars(self._child(child_id).id)

    def give_stars(self, child_id: str, stars: int) -> int:
        """A parent gives a child some stars, as a present; says how many they have now."""
        child = self._child(child_id)
        now = self._clock.now()
        self._days.give_stars(child, stars, app_day(now, self._settings.settings().day_starts_at), now)
        self._events.config_changed("stars", "given", child=child, changes={"gift": stars})
        return self._days.stars(child.id)

    def take_stars(self, child_id: str, stars: int) -> int:
        """A parent takes some stars away (Padres · Niño); never more than they have."""
        child = self._child(child_id)
        if stars > self._days.stars(child.id):
            raise InvalidError("Not that many stars")
        now = self._clock.now()
        self._days.give_stars(child, -stars, app_day(now, self._settings.settings().day_starts_at), now, "taken")
        self._events.config_changed("stars", "taken", child=child, changes={"gift": -stars})
        return self._days.stars(child.id)

    def note(self, child_id: str, kind: str, mission_id: str | None = None, step_id: str | None = None) -> None:
        """Something only worth logging: a mission opened, a task listened to,
        a mission touched while it is not open, or the prize while locked."""
        today = self.today(child_id)
        if kind == "prize_locked":
            if today.prize and today.prize.state == LOCKED:
                self._events.child_did("prize_locked", today.child)
            return
        if mission_id is None:
            raise NotFoundError("Mission not found today")
        item = self._mission_today(today, mission_id)
        step = item.item(step_id) if step_id else None
        if step_id and step is None:
            raise NotFoundError("Step not found")
        schedule = item.schedule
        locked = {
            UPCOMING: schedule and ("opens", schedule.start),
            CLOSED: schedule and ("closed", schedule.end),
        }.get(item.state)
        if kind == "mission_locked" and not locked:
            return  # it is open: nothing to say
        self._events.child_did(kind, today.child, mission=item.mission, step=step, locked=locked or None)

    # ---------- helpers ----------

    @staticmethod
    def _state(schedule: Schedule | None, done: bool, opened: bool, time: str) -> str:
        if done:
            return DONE
        if opened:
            return OPEN
        if schedule and time < schedule.start:
            return UPCOMING
        if schedule and schedule.end and time >= schedule.end:
            return CLOSED
        return OPEN

    def _child(self, child_id: str) -> Child:
        child = self._children.get(child_id)
        if child is None:
            raise NotFoundError("Child not found")
        return child

    @staticmethod
    def _mission_today(today: Today, mission_id: str) -> MissionToday:
        item = next((m for m in today.missions if m.mission.id == mission_id), None)
        if item is None:
            raise NotFoundError("Mission not found today")
        return item
