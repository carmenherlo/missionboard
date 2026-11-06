from datetime import date, datetime
from pathlib import Path

from app.children.repository import Child
from app.storage import db

BACKGROUND_EXTENSIONS = (".webp", ".png", ".jpg", ".jpeg")


class DayRepository:
    """What each child has done each app day, and their stars (SQLite)."""

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
                (day.isoformat(), child.id, mission.id, child.name, mission.name, stars,
                 at.isoformat(timespec="seconds")),
            ).rowcount
            if inserted and stars:
                conn.execute(
                    "INSERT INTO star_movements"
                    " (child_id, child_name, amount, reason, mission_id, mission_name, day, at)"
                    " VALUES (?, ?, ?, 'mission_completed', ?, ?, ?, ?)",
                    (child.id, child.name, stars, mission.id, mission.name, day.isoformat(),
                     at.isoformat(timespec="seconds")),
                )
        return bool(inserted)

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

    def prize_spins(self, day: date, child_id: str) -> list[dict]:
        """The prizes the child won today, in order: {"prize_id", "text", "image"}."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute(
                "SELECT prize_id, prize_text, prize_image FROM prize_spins WHERE day = ? AND child_id = ? ORDER BY id",
                (day.isoformat(), child_id),
            ).fetchall()
        return [{"prize_id": r["prize_id"], "text": r["prize_text"], "image": r["prize_image"]} for r in rows]

    def add_prize_spin(self, day: date, child, prize, at: datetime) -> None:
        with db.connect(self._data_dir) as conn:
            conn.execute(
                "INSERT INTO prize_spins (day, child_id, child_name, prize_id, prize_text, prize_image, at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (day.isoformat(), child.id, child.name, prize.id, prize.text, prize.image,
                 at.isoformat(timespec="seconds")),
            )

    def stars(self, child_id: str) -> int:
        with db.connect(self._data_dir) as conn:
            return conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM star_movements WHERE child_id = ?", (child_id,)
            ).fetchone()[0]


class BackgroundStore:
    """The illustrations of the moments of the day, in personal/backgrounds/<moment>.<ext>.

    They live with the family's data, outside the repo: they can be changed
    (or drawn again) without touching the code.
    """

    def __init__(self, data_dir: Path):
        self._dir = data_dir / "backgrounds"

    def path(self, name: str) -> Path | None:
        for extension in BACKGROUND_EXTENSIONS:
            candidate = self._dir / f"{name}{extension}"
            if candidate.is_file():
                return candidate
        return None

    def version(self, name: str) -> int | None:
        """Changes when the file changes, so the browser fetches the new one."""
        path = self.path(name)
        return int(path.stat().st_mtime) if path else None
