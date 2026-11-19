from datetime import date, datetime
from pathlib import Path

from app.storage import db


class PrizeSpinsRepository:
    """The prizes each child won on the wheel (SQLite `prize_spins`), with a copy of the
    prize's text and image, and when a parent handed it over."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def won(self, day: date, child_id: str) -> list[dict]:
        """The prizes the child won that day, in order: {"prize_id", "text", "image"}."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute(
                "SELECT prize_id, prize_text, prize_image FROM prize_spins WHERE day = ? AND child_id = ? ORDER BY id",
                (day.isoformat(), child_id),
            ).fetchall()
        return [{"prize_id": r["prize_id"], "text": r["prize_text"], "image": r["prize_image"]} for r in rows]

    def add(self, day: date, child, prize, at: datetime) -> None:
        with db.connect(self._data_dir) as conn:
            conn.execute(
                "INSERT INTO prize_spins (day, child_id, child_name, prize_id, prize_text, prize_image, at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    day.isoformat(),
                    child.id,
                    child.name,
                    prize.id,
                    prize.text,
                    prize.image,
                    at.isoformat(timespec="seconds"),
                ),
            )

    def spins_of(self, day: date, child_id: str) -> list[dict]:
        """The wheel's spins of a child that day, whole rows (a card is used once handed over)."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute(
                "SELECT * FROM prize_spins WHERE day = ? AND child_id = ? ORDER BY id", (day.isoformat(), child_id)
            ).fetchall()
        return [dict(row) for row in rows]

    def remove(self, spin_id: int) -> None:
        """A gift card not earned after all (a mission undone), while still unused."""
        with db.connect(self._data_dir) as conn:
            conn.execute("DELETE FROM prize_spins WHERE id = ? AND delivered_at IS NULL", (spin_id,))

    def to_give(self) -> list[dict]:
        """Prizes of the wheel not handed over yet, oldest first."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute(
                "SELECT id, day, child_id, child_name, prize_text, prize_image, at FROM prize_spins"
                " WHERE delivered_at IS NULL ORDER BY id"
            ).fetchall()
        return [dict(row) for row in rows]

    def get(self, spin_id: int) -> dict | None:
        with db.connect(self._data_dir) as conn:
            row = conn.execute("SELECT * FROM prize_spins WHERE id = ?", (spin_id,)).fetchone()
        return dict(row) if row else None

    def deliver(self, spin_id: int, at: datetime) -> None:
        with db.connect(self._data_dir) as conn:
            conn.execute(
                "UPDATE prize_spins SET delivered_at = ? WHERE id = ? AND delivered_at IS NULL",
                (at.isoformat(timespec="seconds"), spin_id),
            )

    def undeliver(self, spin_id: int) -> None:
        """Back to not handed over (a gift card picked by mistake)."""
        with db.connect(self._data_dir) as conn:
            conn.execute("UPDATE prize_spins SET delivered_at = NULL WHERE id = ?", (spin_id,))
