from datetime import date, datetime
from pathlib import Path

from app.storage import db


class StreaksRepository:
    """Rachas (rachas.html), in SQLite: the days a parent let off (`free_days`), the tanks
    loaded into the rocket (`fuel_loads`) and each settled week with its prize
    (`streak_weeks`). Which missions were completed is in today/repository.py."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def free_days(self, child_id: str) -> set[str]:
        with db.connect(self._data_dir) as conn:
            rows = conn.execute("SELECT day FROM free_days WHERE child_id = ?", (child_id,)).fetchall()
        return {row["day"] for row in rows}

    def set_free_day(self, child_id: str, day: date, free: bool, at: datetime) -> None:
        with db.connect(self._data_dir) as conn:
            if free:
                conn.execute(
                    "INSERT OR IGNORE INTO free_days (child_id, day, at) VALUES (?, ?, ?)",
                    (child_id, day.isoformat(), at.isoformat(timespec="seconds")),
                )
            else:
                conn.execute("DELETE FROM free_days WHERE child_id = ? AND day = ?", (child_id, day.isoformat()))

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
                (child_id, day.isoformat(), at.isoformat(timespec="seconds")),
            )
        return cursor.rowcount > 0

    def weeks(self, child_id: str) -> dict[str, dict]:
        """The weeks already settled for the child, by their last day."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute("SELECT * FROM streak_weeks WHERE child_id = ?", (child_id,)).fetchall()
        return {row["week_end"]: dict(row) for row in rows}

    def settle_week(
        self,
        child,
        end: date,
        tier: str,
        prize_text: str,
        full: int,
        days: int,
        at: datetime,
        prize_image: str | None = None,
    ) -> None:
        with db.connect(self._data_dir) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO streak_weeks"
                " (child_id, child_name, week_end, tier, prize_text, full_days, days, at, prize_image)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    child.id,
                    child.name,
                    end.isoformat(),
                    tier,
                    prize_text,
                    full,
                    days,
                    at.isoformat(timespec="seconds"),
                    prize_image,
                ),
            )

    def week_seen(self, child_id: str, end: str, at: datetime) -> None:
        with db.connect(self._data_dir) as conn:
            conn.execute(
                "UPDATE streak_weeks SET shown_at = ? WHERE child_id = ? AND week_end = ? AND shown_at IS NULL",
                (at.isoformat(timespec="seconds"), child_id, end),
            )

    def week_prizes_to_give(self) -> list[dict]:
        """The prizes of a week not handed over yet, oldest first."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute(
                "SELECT * FROM streak_weeks WHERE tier != 'none' AND delivered_at IS NULL ORDER BY week_end, child_name"
            ).fetchall()
        return [dict(row) for row in rows]

    def deliver_week_prize(self, child_id: str, end: str, at: datetime) -> bool:
        with db.connect(self._data_dir) as conn:
            cursor = conn.execute(
                "UPDATE streak_weeks SET delivered_at = ? WHERE child_id = ? AND week_end = ? AND tier != 'none'"
                " AND delivered_at IS NULL",
                (at.isoformat(timespec="seconds"), child_id, end),
            )
        return cursor.rowcount > 0
