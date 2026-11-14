"""Rachas (rachas.html, 13/11): a child's week as fuel tanks, one per day that counts.

The week ends on the day the parents give its prize (settings.streak_week.prize_day)
and starts the day after the previous one. A tank is a day that counts for the week
(one of streak_week.days) on which the child has missions; its state:

- "full": the day was done (streak_rule: all their missions, or at least one);
- "free": a parent let it off (ill, away): it neither counts nor breaks the week;
- "missed": over, and not done;
- "now": today, not done yet;
- "later": still to come.

Once no tank is "now" or "later", the week is closed and its result is a tier:
"full" (every tank that counts), "second" (at least streak_week.second_min, when that
prize is on) or "none". Which missions a day had is read from today's configuration.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.settings.repository import StreakWeek

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
LETTERS = {"mon": "L", "tue": "M", "wed": "X", "thu": "J", "fri": "V", "sat": "S", "sun": "D"}

FULL, FREE, MISSED, NOW, LATER = "full", "free", "missed", "now", "later"


@dataclass
class Tank:
    day: date
    state: str

    @property
    def letter(self) -> str:
        return LETTERS[WEEKDAYS[self.day.weekday()]]


@dataclass
class Week:
    start: date
    end: date
    tanks: list[Tank] = field(default_factory=list)

    @property
    def full(self) -> int:
        return sum(t.state == FULL for t in self.tanks)

    @property
    def counted(self) -> int:
        """The tanks that count: all but the days let off."""
        return sum(t.state != FREE for t in self.tanks)

    @property
    def closed(self) -> bool:
        return bool(self.tanks) and all(t.state in (FULL, FREE, MISSED) for t in self.tanks)

    def tier(self, rules: StreakWeek) -> str:
        if self.counted and self.full == self.counted:
            return "full"
        if rules.second_on and self.full >= rules.second_min:
            return "second"
        return "none"


def week_end(day: date, prize_day: str) -> date:
    """The prize day on or after `day`: the last day of its week."""
    return day + timedelta(days=(WEEKDAYS.index(prize_day) - day.weekday()) % 7)


def build_week(today: date, end: date, rules: StreakWeek, rule: str, had: Callable[[date], set[str]],
               done: dict[str, set[str]], free: set[str]) -> Week:
    """The week ending on `end` as it is on `today`. had(day): the missions the child had
    that day; done: what they completed, by day; free: the days let off."""
    week = Week(start=end - timedelta(days=6), end=end)
    for n in range(7):
        day = week.start + timedelta(days=n)
        missions = had(day)
        if WEEKDAYS[day.weekday()] not in rules.days or not missions:
            continue
        completed = done.get(day.isoformat(), set()) & missions
        kept = completed == missions if rule == "all" else bool(completed)
        if day.isoformat() in free:
            state = FREE
        elif kept:
            state = FULL
        elif day < today:
            state = MISSED
        else:
            state = NOW if day == today else LATER
        week.tanks.append(Tank(day, state))
    return week
