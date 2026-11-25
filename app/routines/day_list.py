"""Rutinas de hoy (padres-barra.html, 25/11): every routine that goes on today, for the
parents' Hoy. Those that ring at a time with their hours, «later» or «over» (done today,
or past its end); those started by hand, «ready» (the parents' screen offers «Lanzar»).
The one going on is known from /current."""

from app.routines.model import Routine
from app.routines.timing import hhmm


def routines_of_day(routines: list[Routine], weekday: str, now_minute: int, finished: set[str]) -> list[dict]:
    found = []
    for stored in routines:
        if not stored.goes_on(weekday):
            continue
        routine = stored.on(weekday)
        item = {"id": routine.id, "name": routine.name, "manual": routine.manual, "minutes": routine.length}
        if routine.manual:
            found.append({**item, "starts": None, "ends": None, "state": "ready"})
        else:
            over = routine.id in finished or now_minute >= routine.ends
            found.append({**item, "starts": hhmm(routine.starts), "ends": hhmm(routine.ends),
                          "state": "over" if over else "later"})  # fmt: skip
    return sorted(found, key=lambda r: (r["manual"], r["starts"] or ""))
