import json
from datetime import date, datetime
from pathlib import Path

from app.storage import db


class DaySnapshotsRepository:
    """In SQLite `day_snapshots`: how the app had left a child's day before a parent first
    changed it (semana-misiones.html), so «Deshacer cambios» can bring it back."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def get(self, child_id: str, day: date) -> dict | None:
        with db.connect(self._data_dir) as conn:
            row = conn.execute(
                "SELECT snapshot FROM day_snapshots WHERE child_id = ? AND day = ?", (child_id, day.isoformat())
            ).fetchone()
        return json.loads(row["snapshot"]) if row else None

    def keep_first(self, child_id: str, day: date, snapshot: dict, at: datetime) -> None:
        """Saved only the first time: later changes keep the app's original."""
        with db.connect(self._data_dir) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO day_snapshots (child_id, day, snapshot, at) VALUES (?, ?, ?, ?)",
                (child_id, day.isoformat(), json.dumps(snapshot), at.isoformat(timespec="seconds")),
            )

    def delete(self, child_id: str, day: date) -> None:
        with db.connect(self._data_dir) as conn:
            conn.execute("DELETE FROM day_snapshots WHERE child_id = ? AND day = ?", (child_id, day.isoformat()))
