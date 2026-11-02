from dataclasses import asdict, dataclass, fields
from datetime import date, datetime
from pathlib import Path

from app.storage import db


@dataclass
class Event:
    """Something that happened in the app, with the names it had at that moment.

    at: when it happened (local time with its offset); day: the app's day,
    which starts at settings.day_starts_at. subject and action say what
    kind of thing it was about and what was done to it (for config_changed:
    "mission" and "changed"; for screen_opened, subject is the screen).
    """

    at: datetime
    day: date
    zone: str | None  # "child" | "parents" | None (nobody in particular: the home screen)
    type: str
    subject: str | None = None
    action: str | None = None
    child_id: str | None = None
    child_name: str | None = None
    mission_id: str | None = None
    mission_name: str | None = None
    step_id: str | None = None
    step_text: str | None = None
    detail: str | None = None
    id: int | None = None


_COLUMNS = [f.name for f in fields(Event) if f.name != "id"]


def _to_row(event: Event) -> dict:
    row = asdict(event)
    row["at"] = event.at.isoformat(timespec="seconds")
    row["day"] = event.day.isoformat()
    row["zone"] = event.zone or ""  # the column is NOT NULL: "" is no zone
    return row


def _from_row(row) -> Event:
    data = dict(row)
    data["at"] = datetime.fromisoformat(data["at"])
    data["day"] = date.fromisoformat(data["day"])
    data["zone"] = data["zone"] or None
    return Event(**data)


class EventsRepository:
    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def add(self, event: Event) -> None:
        placeholders = ", ".join(f":{name}" for name in _COLUMNS)
        with db.connect(self._data_dir) as conn:
            sql = f"INSERT INTO events ({', '.join(_COLUMNS)}) VALUES ({placeholders})"
            conn.execute(sql, _to_row(event))

    def count(self) -> int:
        with db.connect(self._data_dir) as conn:
            return conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def first_day(self) -> date | None:
        with db.connect(self._data_dir) as conn:
            day = conn.execute("SELECT MIN(day) FROM events").fetchone()[0]
        return date.fromisoformat(day) if day else None

    def latest(self, limit: int) -> list[Event]:
        """The most recent first."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [_from_row(row) for row in rows]

    def all(self) -> list[Event]:
        """In the order they happened."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute("SELECT * FROM events ORDER BY id").fetchall()
        return [_from_row(row) for row in rows]
