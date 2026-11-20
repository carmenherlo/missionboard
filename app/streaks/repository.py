from datetime import date, datetime
from pathlib import Path

from app.storage import db


def _at(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


class StreaksRepository:
    """Rachas, in SQLite: when each child's racha started (`streak_starts`), the tanks loaded
    into the rocket (`fuel_loads`) and what happened to each week (`streak_weeks`: launched,
    handed over, and its result once it can no longer change). A week's result is not stored
    while it can change: StreaksService works it out. Which missions were completed is in
    today/repository.py; the days let off, in day_off/."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    # ---------- the start ----------

    def start(self, child_id: str, today: date) -> date:
        """The day the child's racha started: today, the first time it is asked."""
        with db.connect(self._data_dir) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO streak_starts (child_id, day) VALUES (?, ?)", (child_id, today.isoformat())
            )
            row = conn.execute("SELECT day FROM streak_starts WHERE child_id = ?", (child_id,)).fetchone()
        return date.fromisoformat(row["day"])

    def restart(self) -> None:
        """Rachas switched on again: every child's starts on the next look."""
        with db.connect(self._data_dir) as conn:
            conn.execute("DELETE FROM streak_starts")

    # ---------- the fuel ----------

    def fuel_loads(self, child_id: str) -> set[str]:
        """The days whose tank the child loaded into the rocket."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute("SELECT day FROM fuel_loads WHERE child_id = ?", (child_id,)).fetchall()
        return {row["day"] for row in rows}

    def load_fuel(self, child_id: str, day: date, at: datetime) -> bool:
        """False if it was loaded already."""
        with db.connect(self._data_dir) as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO fuel_loads (child_id, day, at) VALUES (?, ?, ?)",
                (child_id, day.isoformat(), _at(at)),
            )
        return cursor.rowcount > 0

    # ---------- the weeks ----------

    def weeks(self, child_id: str) -> dict[str, dict]:
        """What happened to the child's weeks, by their last day."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute("SELECT * FROM streak_weeks WHERE child_id = ?", (child_id,)).fetchall()
        return {row["week_end"]: dict(row) for row in rows}

    def all_weeks(self) -> list[dict]:
        with db.connect(self._data_dir) as conn:
            rows = conn.execute("SELECT * FROM streak_weeks ORDER BY week_end, child_name").fetchall()
        return [dict(row) for row in rows]

    def _ensure(self, conn, child, end: str) -> None:
        conn.execute(
            "INSERT OR IGNORE INTO streak_weeks (child_id, child_name, week_end) VALUES (?, ?, ?)",
            (child.id, child.name, end),
        )

    def launched(self, child, end: str, tier: str, prize_text: str, prize_image: str | None, at: datetime) -> None:
        """The child saw how the week ended, in the workshop: with this tier and this prize."""
        with db.connect(self._data_dir) as conn:
            self._ensure(conn, child, end)
            conn.execute(
                "UPDATE streak_weeks SET launched_at = ?, launched_tier = ?, prize_text = ?, prize_image = ?"
                " WHERE child_id = ? AND week_end = ?",
                (_at(at), tier, prize_text, prize_image, child.id, end),
            )

    def freeze(self, child, end: str, tier: str, full: int, days: int, prize_text: str, prize_image, at) -> None:
        """The week can no longer change: its final result."""
        with db.connect(self._data_dir) as conn:
            self._ensure(conn, child, end)
            conn.execute(
                "UPDATE streak_weeks SET tier = ?, full_days = ?, days = ?, frozen_at = ?, prize_text = ?,"
                " prize_image = ? WHERE child_id = ? AND week_end = ?",
                (tier, full, days, _at(at), prize_text, prize_image, child.id, end),
            )

    def deliver(self, child, end: str, at: datetime) -> bool:
        with db.connect(self._data_dir) as conn:
            self._ensure(conn, child, end)
            cursor = conn.execute(
                "UPDATE streak_weeks SET delivered_at = ? WHERE child_id = ? AND week_end = ? AND delivered_at IS NULL",
                (_at(at), child.id, end),
            )
        return cursor.rowcount > 0

    def undeliver_week_prize(self, child_id: str, end: str) -> None:
        with db.connect(self._data_dir) as conn:
            conn.execute(
                "UPDATE streak_weeks SET delivered_at = NULL WHERE child_id = ? AND week_end = ?", (child_id, end)
            )
