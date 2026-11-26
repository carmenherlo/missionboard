"""Races (SQLite `races`, modo-carrera.html): each race that ended, with how it went.
A lost race only loses its extra stars: its mission goes on as any other (24/11)."""

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
        ghost_share: float | None = None,
        tasks: list[dict] | None = None,
    ) -> int:
        """`kids`: the children who ran it (a copy of their names); `given` None: waiting for a parent."""
        with db.connect(self._data_dir) as conn:
            cursor = conn.execute(
                "INSERT INTO races (day, routine_id, routine_name, mission_id, kids, planned_seconds, took_seconds,"
                " outcome, stars, at, given, ghost_share, tasks) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                    ghost_share,
                    tasks and json.dumps(tasks),
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

    def recent(self, routine_id: str, limit: int) -> list[dict]:
        """This routine's last races, newest first (the alien learns from them)."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute(
                "SELECT * FROM races WHERE routine_id = ? ORDER BY id DESC LIMIT ?", (routine_id, limit)
            ).fetchall()
        return [_race(row) for row in rows]

    def reviewed(self, race_id: int, given: bool, at: datetime) -> None:
        with db.connect(self._data_dir) as conn:
            conn.execute(
                "UPDATE races SET given = ?, reviewed_at = ? WHERE id = ?",
                (int(given), at.isoformat(timespec="seconds"), race_id),
            )

    def set_redo(self, race_id: int, task_ids: list[str]) -> None:
        with db.connect(self._data_dir) as conn:
            conn.execute("UPDATE races SET redo = ? WHERE id = ?", (json.dumps(task_ids), race_id))

    def tips(self, routine_id: str) -> dict[str, int]:
        """How many times the voice explained each new thing in this routine's races."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute("SELECT tip, times FROM race_tips WHERE routine_id = ?", (routine_id,)).fetchall()
        return {row["tip"]: row["times"] for row in rows}

    def tip_said(self, routine_id: str, tip: str) -> None:
        with db.connect(self._data_dir) as conn:
            conn.execute(
                "INSERT INTO race_tips (routine_id, tip, times) VALUES (?, ?, 1)"
                " ON CONFLICT (routine_id, tip) DO UPDATE SET times = times + 1",
                (routine_id, tip),
            )


def _race(row) -> dict:
    race = dict(row)
    race["kids"] = json.loads(race["kids"])
    race["tasks"] = race["tasks"] and json.loads(race["tasks"])
    race["redo"] = json.loads(race["redo"]) if race["redo"] else []
    race["given"] = None if race["given"] is None else bool(race["given"])
    return race
