"""A child's day: which missions they have today, in which state, and what
happens when they check a step. The rules are here; the screens only show them.

States of a mission today (paso-4.html, "Las reglas del día"):
- done: every step checked today. It stays done until tomorrow.
- open: no schedule, or inside it. Steps can be checked and unchecked.
- upcoming: before its start time. It cannot be opened yet.
- closed: past its end time without being done. No star.
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
from app.missions.repository import WEEKDAYS, Mission, MissionsRepository
from app.prizes.repository import Prize, PrizesRepository
from app.settings import Moment, SettingsRepository
from app.today.repository import DayRepository

DONE, OPEN, UPCOMING, CLOSED = "done", "open", "upcoming", "closed"
LOCKED, UNLOCKED, WON = "locked", "unlocked", "won"

# What a child can do on the route that only goes to the event log.
NOTES = ("mission_opened", "step_spoken", "mission_locked", "prize_locked")


@dataclass
class MissionToday:
    mission: Mission
    state: str
    checked: set[str] = field(default_factory=set)
    focus: bool = False


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
    moment: Moment
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


def current_moment(moments: tuple[Moment, ...], time: str) -> Moment:
    """The last moment that has started; before the first one, the night goes on."""
    started = [m for m in moments if m.start <= time]
    return started[-1] if started else moments[-1]


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
        choose=secrets.choice,  # tests pass their own, to know the prize
    ):
        self._children = children
        self._missions = missions
        self._days = days
        self._settings = settings
        self._clock = clock
        self._events = events
        self._prizes = prizes
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
        missions = []
        for mission in self._missions.list_for_child(child.id):
            # Not today, or nothing to check yet (a mission still being written)
            if weekday not in mission.days or not mission.steps:
                continue
            step_ids = {s.id for s in mission.steps}
            missions.append(MissionToday(
                mission=mission,
                state=self._state(mission, mission.id in completed, time),
                checked=checked.get(mission.id, set()) & step_ids,
            ))

        focus = next((m for m in missions if m.state == OPEN), None)
        focus = focus or next((m for m in missions if m.state == UPCOMING), None)
        if focus:
            focus.focus = True
        return Today(
            child=child,
            day=day,
            moment=current_moment(settings.moments, time),
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

    def set_step(self, child_id: str, mission_id: str, step_id: str, checked: bool) -> StepResult:
        """Check or uncheck a step. Checking the last one completes the mission (once a day)."""
        today = self.today(child_id)
        item = self._mission_today(today, mission_id)
        step = next((s for s in item.mission.steps if s.id == step_id), None)
        if step is None:
            raise NotFoundError("Step not found")
        if item.state == DONE:
            if not checked:
                raise ConflictError("The mission is already done today")
            return StepResult(today, completed=False, stars_earned=0)
        if item.state != OPEN:
            raise ConflictError("The mission is not open now")
        if (step_id in item.checked) == checked:
            return StepResult(today, completed=False, stars_earned=0)

        now = self._clock.now()
        self._days.set_step(today.day, today.child.id, mission_id, step_id, checked, now)
        self._events.child_did(
            "step_checked" if checked else "step_unchecked", today.child, mission=item.mission, step=step
        )

        all_checked = (item.checked | {step_id}) >= {s.id for s in item.mission.steps}
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

    def note(self, child_id: str, kind: str, mission_id: str | None = None, step_id: str | None = None) -> None:
        """Something only worth logging: a mission opened, a step listened to,
        a mission touched while it is not open, or the prize while locked."""
        today = self.today(child_id)
        if kind == "prize_locked":
            if today.prize and today.prize.state == LOCKED:
                self._events.child_did("prize_locked", today.child)
            return
        if mission_id is None:
            raise NotFoundError("Mission not found today")
        item = self._mission_today(today, mission_id)
        step = next((s for s in item.mission.steps if s.id == step_id), None) if step_id else None
        if step_id and step is None:
            raise NotFoundError("Step not found")
        schedule = item.mission.schedule
        locked = {
            UPCOMING: schedule and ("opens", schedule.start),
            CLOSED: schedule and ("closed", schedule.end),
        }.get(item.state)
        if kind == "mission_locked" and not locked:
            return  # it is open: nothing to say
        self._events.child_did(kind, today.child, mission=item.mission, step=step, locked=locked or None)

    # ---------- helpers ----------

    @staticmethod
    def _state(mission: Mission, done: bool, time: str) -> str:
        if done:
            return DONE
        schedule = mission.schedule
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
