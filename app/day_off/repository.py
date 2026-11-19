from datetime import date, datetime
from pathlib import Path

from app.storage import db

WHOLE_DAY = ""  # mission_id of a row that lets the whole day off


class DayOffsRepository:
    """Días libres (dias-libres.html), in SQLite `day_offs`: per child and day, the whole
    day (mission_id '') or some missions a parent let off, with an optional sentence."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def by_day(self, child_id: str) -> dict[str, dict[str, str]]:
        """Every day with something off: {"2026-11-19": {mission_id or '': phrase}}."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute(
                "SELECT day, mission_id, phrase FROM day_offs WHERE child_id = ?", (child_id,)
            ).fetchall()
        days: dict[str, dict[str, str]] = {}
        for row in rows:
            days.setdefault(row["day"], {})[row["mission_id"]] = row["phrase"]
        return days

    def on(self, child_id: str, day: date) -> dict[str, str]:
        """What is off that day: {mission_id or '': phrase}."""
        return self.by_day(child_id).get(day.isoformat(), {})

    def replace(self, child_id: str, day: date, off: set[str], phrase: str, at: datetime) -> None:
        """What is off that day, all at once (WHOLE_DAY for the whole day)."""
        with db.connect(self._data_dir) as conn:
            conn.execute("DELETE FROM day_offs WHERE child_id = ? AND day = ?", (child_id, day.isoformat()))
            conn.executemany(
                "INSERT INTO day_offs (child_id, day, mission_id, phrase, at) VALUES (?, ?, ?, ?, ?)",
                [(child_id, day.isoformat(), m, phrase, at.isoformat(timespec="seconds")) for m in sorted(off)],
            )

    def remove(self, child_id: str, day: date, mission_id: str) -> None:
        with db.connect(self._data_dir) as conn:
            conn.execute(
                "DELETE FROM day_offs WHERE child_id = ? AND day = ? AND mission_id = ?",
                (child_id, day.isoformat(), mission_id),
            )
