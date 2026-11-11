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
from datetime import date

from app.children.repository import Child, ChildrenRepository
from app.clock import Clock, app_day
from app.errors import ConflictError, NotFoundError
from app.events.service import EventLog
from app.missions.repository import WEEKDAYS, ChildTask, Mission, MissionsRepository, Schedule, child_tasks
from app.prizes.repository import Prize, PrizesRepository
from app.routines import links
from app.routines.repository import RoutinesRepository, minute_of
from app.settings import MOMENTS, Season, SettingsRepository
from app.today.repository import DayRepository

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
            item.checked = checked.get(mission.id, set()) & set(item.marks)
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
        )

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
        """Check or uncheck a step, or a task without steps. The last one completes the
        mission (once a day). Checking a task that has steps does nothing by itself."""
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
