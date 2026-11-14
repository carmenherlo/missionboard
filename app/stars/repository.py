from datetime import date, datetime
from pathlib import Path

from app.children.repository import Child
from app.storage import db


class StarsRepository:
    """A child's stars (SQLite `star_movements`): every star in or out is a movement and
    the balance is their sum. A mission's star is written with its completion, in one
    transaction (today/repository.py); a purchase, with its order (shop/repository.py)."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def balance(self, child_id: str) -> int:
        with db.connect(self._data_dir) as conn:
            return conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM star_movements WHERE child_id = ?", (child_id,)
            ).fetchone()[0]

    def add_starting_stars(self, child: Child, stars: int, day: date, at: datetime) -> None:
        """What a new child starts with (settings.starting_stars)."""
        if not stars:
            return
        with db.connect(self._data_dir) as conn:
            conn.execute(
                "INSERT INTO star_movements (child_id, child_name, amount, reason, day, at)"
                " VALUES (?, ?, ?, 'starting_stars', ?, ?)",
                (child.id, child.name, stars, day.isoformat(), at.isoformat(timespec="seconds")),
            )

    def give(self, child: Child, stars: int, day: date, at: datetime, reason: str = "gift") -> None:
        """Stars a parent gives a child, as a present (reason "gift"), or takes away
        (reason "taken", stars negative)."""
        with db.connect(self._data_dir) as conn:
            conn.execute(
                "INSERT INTO star_movements (child_id, child_name, amount, reason, day, at) VALUES (?, ?, ?, ?, ?, ?)",
                (child.id, child.name, stars, reason, day.isoformat(), at.isoformat(timespec="seconds")),
            )

    def movements(self, child_id: str, limit: int) -> list[dict]:
        """The latest stars in and out, newest first."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute(
                "SELECT amount, reason, mission_name, day, at FROM star_movements WHERE child_id = ?"
                " ORDER BY at DESC, id DESC LIMIT ?",
                (child_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def earned_by_day(self, child_id: str, since: date) -> dict[str, int]:
        """Stars won with missions, by day, from `since`."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute(
                "SELECT day, SUM(amount) AS stars FROM star_movements"
                " WHERE child_id = ? AND reason = 'mission_completed' AND day >= ? GROUP BY day",
                (child_id, since.isoformat()),
            ).fetchall()
        return {row["day"]: row["stars"] for row in rows}
