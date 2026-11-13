"""Rachas (step 8): how many days in a row a child has done their missions.

A day counts when the child did what settings.streak_rule asks: "any", at least one
mission; "all", every mission they had that day. Days without missions for them
(a weekend with nothing) neither count nor break it. Today only adds: until it is
done, the streak is the one up to yesterday. Which missions a day had is read from
today's configuration (missions changed later are not remembered).
"""

from collections.abc import Callable
from datetime import date, timedelta

LOOK_BACK_DAYS = 400  # far enough for any child's streak


def streak(today: date, rule: str, had: Callable[[date], set[str]], done: dict[str, set[str]]) -> int:
    """had(day): the missions the child had that day; done: what they completed, by day."""
    count = 0
    for back in range(LOOK_BACK_DAYS):
        day = today - timedelta(days=back)
        missions = had(day)
        if not missions:
            continue
        completed = done.get(day.isoformat(), set()) & missions
        kept = completed == missions if rule == "all" else bool(completed)
        if kept:
            count += 1
        elif day != today:
            break
    return count
