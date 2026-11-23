"""Races (SQLite `races`, modo-carrera.html): each race that ended, with how it went.
A lost race closes its mission for its children from then on (read by the day)."""

import json
from datetime import date, datetime
from pathlib import Path

from app.storage import db


class RacesRepository:
    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def add(
        self,
        day: date,
        routine,
        kids: list,
        *,
        planned_seconds: int,
        took_seconds: int | None,
        outcome: str,
        stars: int,
        at: datetime,
        given: bool | None,
    ) -> int:
        """`kids`: the children who ran it (a copy of their names); `given` None: waiting for a parent."""
        with db.connect(self._data_dir) as conn:
            cursor = conn.execute(
                "INSERT INTO races (day, routine_id, routine_name, mission_id, kids, planned_seconds, took_seconds,"
                " outcome, stars, at, given) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    day.isoformat(),
                    routine.id,
                    routine.name,
                    routine.mission_id,
                    json.dumps([{"id": k.id, "name": k.name} for k in kids]),
                    planned_seconds,
                    took_seconds,
                    outcome,
                    stars,
                    at.isoformat(timespec="seconds"),
                    None if given is None else int(given),
                ),
            )
            return cursor.lastrowid

    def get(self, race_id: int) -> dict | None:
        with db.connect(self._data_dir) as conn:
            row = conn.execute("SELECT * FROM races WHERE id = ?", (race_id,)).fetchone()
        return _race(row) if row else None

    def of_day(self, day: date) -> list[dict]:
        with db.connect(self._data_dir) as conn:
            rows = conn.execute("SELECT * FROM races WHERE day = ? ORDER BY id", (day.isoformat(),)).fetchall()
        return [_race(row) for row in rows]

    def reviewed(self, race_id: int, given: bool, at: datetime) -> None:
        with db.connect(self._data_dir) as conn:
            conn.execute(
                "UPDATE races SET given = ?, reviewed_at = ? WHERE id = ?",
                (int(given), at.isoformat(timespec="seconds"), race_id),
            )

    def closed_missions(self, day: date, child_id: str) -> dict[str, str]:
        """The child's missions closed today by a lost race: mission id → when ("HH:MM")."""
        return {
            race["mission_id"]: race["at"][11:16]
            for race in self.of_day(day)
            if race["outcome"] == "lost" and child_id in {k["id"] for k in race["kids"]}
        }


def _race(row) -> dict:
    race = dict(row)
    race["kids"] = json.loads(race["kids"])
    race["given"] = None if race["given"] is None else bool(race["given"])
    return race
