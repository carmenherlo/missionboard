"""Rachas (20/11): the rules of a child's week of fuel tanks, in one place.
Everything here is worked out from the data each time, never stored: change a day (undo a
mission, mark it done, let it off) and the week simply comes out different.

The week ends on the day the parents give its prize (settings.streak_week.prize_day) and
starts the day after the previous one. A tank is a day that counts (one of streak_week.days)
on which the child has missions, from the day their racha started; its state:

- "full": all their missions done that day;
- "free": a parent let it off (ill, away, or it should not count): it is not counted, nor
  drawn in the workshop, even if its missions were done (the parent decides, 20/11);
- "missed": over, and not done;
- "now": today, not done yet;
- "later": still to come.

Once no tank is "now" or "later", the week is closed and its result is a tier: "full" (every
tank that counts), "second" (at least streak_week.second_percent % of them, when that prize
is on) or "none". A closed week stays open to changes, and in the workshop, until the next
one starts (its first day that counts): then it is over for good.
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
        return self.counted > 0 and all(t.state in (FULL, FREE, MISSED) for t in self.tanks)

    def tier(self, rules: StreakWeek) -> str:
        if self.counted and self.full == self.counted:
            return "full"
        if rules.second_on and self.counted and self.full * 100 >= rules.second_percent * self.counted:
            return "second"
        return "none"


def week_end(day: date, prize_day: str) -> date:
    """The prize day on or after `day`: the last day of its week."""
    return day + timedelta(days=(WEEKDAYS.index(prize_day) - day.weekday()) % 7)


def next_start(end: date, rules: StreakWeek) -> date:
    """The first day that counts after a week's end: from then on, that week is over."""
    day = end + timedelta(days=1)
    while WEEKDAYS[day.weekday()] not in rules.days:
        day += timedelta(days=1)
    return day


def build_week(
    today: date,
    end: date,
    rules: StreakWeek,
    had: Callable[[date], set[str]],
    done: dict[str, set[str]],
    free: set[str],
    since: date | None = None,
) -> Week:
    """The week ending on `end` as it is on `today`. had(day): the missions the child had
    that day; done: what they completed, by day; free: the days let off; since: the day
    their racha started (the days before it are not judged)."""
    week = Week(start=end - timedelta(days=6), end=end)
    for n in range(7):
        day = week.start + timedelta(days=n)
        missions = had(day)
        if WEEKDAYS[day.weekday()] not in rules.days or not missions or (since and day < since):
            continue
        if day.isoformat() in free:
            state = FREE  # the parent's word: the day does not count, whatever was done
        elif done.get(day.isoformat(), set()) >= missions:
            state = FULL
        elif day < today:
            state = MISSED
        else:
            state = NOW if day == today else LATER
        week.tanks.append(Tank(day, state))
    return week


def shown_end(today: date, rules: StreakWeek, has_tanks: Callable[[date], bool]) -> date:
    """The week to show (the workshop, the parents' screens): the one that has just closed,
    until the next one starts, if it had any tank; otherwise this one."""
    end = week_end(today, rules.prize_day)
    previous = end - timedelta(days=7)
    return previous if today < next_start(previous, rules) and has_tanks(previous) else end
