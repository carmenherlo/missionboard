"""Routines in config.yaml (`routines`) and what happened to each one each day (SQLite).

A routine (model.py) goes with one mission, and its parts are that mission's tasks, in their
order: only what is the routine's own is stored (minutes, what the voice says), and
the rest is taken from the mission every time it is read, so they cannot drift apart.
"""

from datetime import date, datetime
from pathlib import Path

from app.missions.repository import WEEKDAYS
from app.routines.model import STORED_PART, Routine
from app.routines.timing import music_kept, settled
from app.storage import db
from app.storage.config_store import ConfigStore

NEW_PART_MINUTES = 5


def resolved(stored: dict, mission: dict) -> dict:
    """A stored routine with what comes from its mission: its name and picture, and its
    tasks as parts, in their order (a new one, 5 minutes), with all their steps. The times
    settle again: tasks may have come or gone."""
    own = {part["id"]: part for part in stored.get("parts") or []}
    first_at = (stored.get("parts") or [{}])[0].get("at")
    mission_days = mission.get("days") or WEEKDAYS
    parts = []
    for task in mission["tasks"]:
        part = own.get(task["id"], {})
        parts.append(
            {
                **{key: part.get(key) for key in STORED_PART},
                "id": task["id"],
                "at": None,
                "minutes": part.get("minutes") or NEW_PART_MINUTES,
                "text": task["text"],
                "name": part.get("spoken") or task["text"][:1].lower() + task["text"][1:],
                "image": task.get("image"),
                "image_suggested": bool(task.get("image_suggested")),
                "days": [d for d in mission_days if not task.get("days") or d in task["days"]],
                "steps": [{"text": step["text"], "image": step.get("image")} for step in task.get("steps") or []],
            }
        )
    if stored.get("wake") is not None:
        parts[0]["at"] = first_at or stored["wake"]
    return music_kept(
        settled(
            {
                **stored,
                "name": mission["name"],
                "image": mission.get("image"),
                "parts": parts,
                "days": [d for d in stored.get("days") or WEEKDAYS if d in mission_days],
            }
        )
    )


def _stored(routine: Routine) -> dict:
    """Only what is the routine's own: the rest comes from its mission when it is read."""
    doc = routine.to_doc()
    del doc["name"], doc["image"]
    doc["parts"] = [{key: part[key] for key in STORED_PART} for part in doc["parts"]]
    return doc


class RoutinesRepository:
    """The `routines` list of config.yaml, read together with their missions."""

    def __init__(self, store: ConfigStore):
        self._store = store

    def atomic(self):
        return self._store.edit()

    def resolve(self, stored: dict) -> dict:
        """A routine not saved yet, as it would be read (its mission must have tasks)."""
        doc = self._store.load()
        mission = next(m for m in doc["missions"] if m["id"] == stored["mission_id"])
        return resolved(stored, mission)

    def live(self) -> list[Routine]:
        """The ones that ring and start: not the ones switched off in their mission."""
        return [r for r in self.list() if not r.off]

    def list(self) -> list[Routine]:
        doc = self._store.load()
        missions = {m["id"]: m for m in doc["missions"]}
        return [
            Routine.model_validate(resolved(entry, missions[entry["mission_id"]]))
            for entry in doc.get("routines") or []
            if missions.get(entry["mission_id"], {}).get("tasks")  # mission without tasks: not a routine yet
        ]

    def get(self, routine_id: str) -> Routine | None:
        return next((r for r in self.list() if r.id == routine_id), None)

    def of_mission(self, mission_id: str) -> Routine | None:
        return next((r for r in self.list() if r.mission_id == mission_id), None)

    def add(self, routine: Routine) -> None:
        with self._store.edit() as doc:
            doc.setdefault("routines", []).append(_stored(routine))

    def update(self, routine: Routine) -> None:
        with self._store.edit() as doc:
            doc["routines"] = [_stored(routine) if r["id"] == routine.id else r for r in doc["routines"]]

    def remove(self, routine_id: str) -> None:
        with self._store.edit() as doc:
            doc["routines"] = [r for r in doc["routines"] if r["id"] != routine_id]

    def remove_of_mission(self, mission_id: str) -> None:
        with self._store.edit() as doc:
            doc["routines"] = [r for r in doc.get("routines") or [] if r["mission_id"] != mission_id]


class RunsRepository:
    """What happened to each routine each day: started, stopped (the alarm) and finished
    (for the day), and, started by hand, since when it is paused and the minutes a parent
    added to its parts (`extra`) and who cheered in a race (`cheers`). `by_hand`: one that
    rings at a time, started by hand today for who was left (rutinas-flexibles.html). `closed_phase` is no
    longer set (16/11: hidden on one device only)."""

    FIELDS = (
        "started_at", "stopped_at", "closed_phase", "finished_at", "kids", "paused_at", "extra", "cheers", "by_hand"
    )  # fmt: skip

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def get(self, day: date, routine_id: str) -> dict:
        with db.connect(self._data_dir) as conn:
            row = conn.execute(
                "SELECT * FROM routine_runs WHERE day = ? AND routine_id = ?", (day.isoformat(), routine_id)
            ).fetchone()
        return {name: row[name] if row else None for name in self.FIELDS}

    def clear(self, day: date, routine_id: str) -> None:
        """Forget today's run (a routine started by hand that ended: it can start again)."""
        with db.connect(self._data_dir) as conn:
            conn.execute("DELETE FROM routine_runs WHERE day = ? AND routine_id = ?", (day.isoformat(), routine_id))

    def set(self, day: date, routine_id: str, **values) -> None:
        assert set(values) <= set(self.FIELDS)
        values = {k: v.isoformat(timespec="seconds") if isinstance(v, datetime) else v for k, v in values.items()}
        columns = ", ".join(values)
        updates = ", ".join(f"{name} = excluded.{name}" for name in values)
        with db.connect(self._data_dir) as conn:
            conn.execute(
                f"INSERT INTO routine_runs (day, routine_id, {columns}) VALUES (?, ?, {', '.join('?' * len(values))})"
                f" ON CONFLICT (day, routine_id) DO UPDATE SET {updates}",
                (day.isoformat(), routine_id, *values.values()),
            )
