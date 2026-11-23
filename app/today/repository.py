from datetime import date, datetime
from pathlib import Path

from app.storage import db


class DayRepository:
    """What each child has done each app day (SQLite). `step_checks` keeps the tasks they
    check (before misiones-3, also steps: see today/service.py). A completed mission puts
    its stars in `star_movements` in the same transaction (the rest of the stars: stars/)."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def checked_steps(self, day: date, child_id: str) -> dict[str, set[str]]:
        """Step ids checked today, by mission id."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute(
                "SELECT mission_id, step_id FROM step_checks WHERE day = ? AND child_id = ?",
                (day.isoformat(), child_id),
            ).fetchall()
        checked: dict[str, set[str]] = {}
        for row in rows:
            checked.setdefault(row["mission_id"], set()).add(row["step_id"])
        return checked

    def completed_missions(self, day: date, child_id: str) -> set[str]:
        with db.connect(self._data_dir) as conn:
            rows = conn.execute(
                "SELECT mission_id FROM mission_completions WHERE day = ? AND child_id = ?",
                (day.isoformat(), child_id),
            ).fetchall()
        return {row["mission_id"] for row in rows}

    def opened_missions(self, day: date, child_id: str) -> dict[str, str]:
        """Missions opened for this child only today (by a parent or a routine): id → last time ("HH:MM")."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute(
                "SELECT mission_id, at FROM mission_openings WHERE day = ? AND child_id = ?",
                (day.isoformat(), child_id),
            ).fetchall()
        return {row["mission_id"]: row["at"][11:16] for row in rows}

    def open_mission(self, day: date, child_id: str, mission_id: str, at: datetime) -> None:
        with db.connect(self._data_dir) as conn:
            conn.execute(
                "INSERT INTO mission_openings (day, child_id, mission_id, at) VALUES (?, ?, ?, ?)"
                " ON CONFLICT (day, child_id, mission_id) DO UPDATE SET at = excluded.at",
                (day.isoformat(), child_id, mission_id, at.isoformat(timespec="seconds")),
            )

    def set_step(self, day: date, child_id: str, mission_id: str, step_id: str, checked: bool, at: datetime):
        with db.connect(self._data_dir) as conn:
            if checked:
                conn.execute(
                    "INSERT OR IGNORE INTO step_checks (day, child_id, mission_id, step_id, at) VALUES (?, ?, ?, ?, ?)",
                    (day.isoformat(), child_id, mission_id, step_id, at.isoformat(timespec="seconds")),
                )
            else:
                conn.execute(
                    "DELETE FROM step_checks WHERE day = ? AND child_id = ? AND mission_id = ? AND step_id = ?",
                    (day.isoformat(), child_id, mission_id, step_id),
                )

    def complete(self, day: date, child, mission, stars: int, at: datetime) -> bool:
        """Mark the mission done today and put its stars in the child's bank.

        Both in one transaction, and only the first time: returns False (and
        changes nothing) if it was already done today.
        """
        with db.connect(self._data_dir) as conn:
            inserted = conn.execute(
                "INSERT OR IGNORE INTO mission_completions"
                " (day, child_id, mission_id, child_name, mission_name, stars, at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    day.isoformat(),
                    child.id,
                    mission.id,
                    child.name,
                    mission.name,
                    stars,
                    at.isoformat(timespec="seconds"),
                ),
            ).rowcount
            if inserted and stars:
                conn.execute(
                    "INSERT INTO star_movements"
                    " (child_id, child_name, amount, reason, mission_id, mission_name, day, at)"
                    " VALUES (?, ?, ?, 'mission_completed', ?, ?, ?, ?)",
                    (
                        child.id,
                        child.name,
                        stars,
                        mission.id,
                        mission.name,
                        day.isoformat(),
                        at.isoformat(timespec="seconds"),
                    ),
                )
        return bool(inserted)

    def completion(self, day: date, child_id: str, mission_id: str) -> dict | None:
        with db.connect(self._data_dir) as conn:
            row = conn.execute(
                "SELECT * FROM mission_completions WHERE day = ? AND child_id = ? AND mission_id = ?",
                (day.isoformat(), child_id, mission_id),
            ).fetchone()
        return dict(row) if row else None

    def uncomplete(self, day: date, child, mission_id: str, stars: int, at: datetime) -> dict | None:
        """A mission marked done by mistake (dias-libres.html, section 6): it is no longer
        done that day, its tasks go back unchecked and `stars` go out of the bank (as a
        movement, so the history keeps both). One transaction; None if it was not done."""
        with db.connect(self._data_dir) as conn:
            row = conn.execute(
                "SELECT * FROM mission_completions WHERE day = ? AND child_id = ? AND mission_id = ?",
                (day.isoformat(), child.id, mission_id),
            ).fetchone()
            if row is None:
                return None
            keys = (day.isoformat(), child.id, mission_id)
            conn.execute("DELETE FROM mission_completions WHERE day = ? AND child_id = ? AND mission_id = ?", keys)
            conn.execute("DELETE FROM step_checks WHERE day = ? AND child_id = ? AND mission_id = ?", keys)
            if stars:
                conn.execute(
                    "INSERT INTO star_movements"
                    " (child_id, child_name, amount, reason, mission_id, mission_name, day, at)"
                    " VALUES (?, ?, ?, 'undone', ?, ?, ?, ?)",
                    (
                        child.id,
                        child.name,
                        -stars,
                        mission_id,
                        row["mission_name"],
                        day.isoformat(),
                        at.isoformat(timespec="seconds"),
                    ),
                )
        return dict(row)

    def completions(self, child_id: str) -> dict[str, set[str]]:
        """Every mission the child has completed, by day ("2026-11-13" → mission ids)."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute(
                "SELECT day, mission_id FROM mission_completions WHERE child_id = ?", (child_id,)
            ).fetchall()
        days: dict[str, set[str]] = {}
        for row in rows:
            days.setdefault(row["day"], set()).add(row["mission_id"])
        return days
