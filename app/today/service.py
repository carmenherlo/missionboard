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

The day also brings what the route shows besides missions: the daily prize at its
end (daily_prize/), the child's stars (stars/) and their streak (streaks/).
"""

from dataclasses import dataclass, field
from datetime import date

from app.children.repository import Child, ChildrenRepository
from app.clock import Clock, app_day
from app.daily_prize.state import LOCKED, UNLOCKED, PrizeBoard, PrizeToday
from app.errors import ConflictError, NotFoundError
from app.events.service import EventLog
from app.missions.repository import WEEKDAYS, ChildTask, Mission, MissionsRepository, Schedule, child_tasks
from app.routines import links
from app.routines.repository import RoutinesRepository
from app.settings import Season, SettingsRepository
from app.stars.service import StarsService
from app.streaks.service import StreaksService
from app.today.repository import DayRepository
from app.today.season import current_moment, current_season

DONE, OPEN, UPCOMING, CLOSED = "done", "open", "upcoming", "closed"

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


def _checked_tasks(tasks: list[ChildTask], checked: set[str]) -> set[str]:
    """The tasks checked today. Before misiones-3 a child checked steps: a task whose
    steps were all checked that day counts as checked too, so nobody loses it."""
    return {
        task.task.id
        for task in tasks
        if task.task.id in checked or (task.steps and all(s.id in checked for s in task.steps))
    }


class DayService:
    def __init__(
        self,
        children: ChildrenRepository,
        missions: MissionsRepository,
        days: DayRepository,
        settings: SettingsRepository,
        clock: Clock,
        events: EventLog,
        routines: RoutinesRepository,
        prize: PrizeBoard,
        stars: StarsService,
        streaks: StreaksService,
    ):
        self._children = children
        self._missions = missions
        self._days = days
        self._settings = settings
        self._clock = clock
        self._events = events
        self._routines = routines
        self._prize = prize
        self._stars = stars
        self._streaks = streaks

    def today(self, child_id: str) -> Today:
        child = self._children.require(child_id)
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
            item = MissionToday(
                mission,
                self._state(schedule, mission.id in completed, mission.id in opened, time),
                tasks,
                schedule=schedule,
            )
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
            stars=self._stars.balance(child.id),
            prize=self._prize.today(day, child, len(missions), all(m.state == DONE for m in missions)),
            streak=self._streaks.streak(child.id, day) if self._settings.features().streaks else None,
        )

    def set_mark(self, child_id: str, mission_id: str, item_id: str, checked: bool) -> StepResult:  # noqa: C901 (to split)
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

    @staticmethod
    def _mission_today(today: Today, mission_id: str) -> MissionToday:
        item = next((m for m in today.missions if m.mission.id == mission_id), None)
        if item is None:
            raise NotFoundError("Mission not found today")
        return item
