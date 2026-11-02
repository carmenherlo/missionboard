from dataclasses import asdict, dataclass, field

from app.storage.config_store import ConfigStore

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@dataclass
class Step:
    id: str
    text: str
    image: str | None = None
    image_suggested: bool = False  # chosen by the app; cleared when a parent sets the image


@dataclass
class Schedule:
    start: str
    end: str | None = None


@dataclass
class Mission:
    """A mission of one child. Its position in the child's list is the order of their route.

    A template has the same shape, without a child (child_id is None).
    """

    id: str
    child_id: str | None
    name: str
    image: str | None = None
    image_suggested: bool = False
    days: list[str] = field(default_factory=lambda: list(WEEKDAYS))
    schedule: Schedule | None = None
    steps: list[Step] = field(default_factory=list)


def _to_doc(mission: Mission) -> dict:
    doc = asdict(mission)
    if mission.child_id is None:
        del doc["child_id"]
    return doc


def _from_doc(entry: dict) -> Mission:
    schedule = entry.get("schedule")
    return Mission(
        id=entry["id"],
        child_id=entry.get("child_id"),
        name=entry["name"],
        image=entry.get("image"),
        image_suggested=bool(entry.get("image_suggested", False)),
        days=list(entry.get("days") or WEEKDAYS),
        schedule=Schedule(start=schedule["start"], end=schedule.get("end")) if schedule else None,
        steps=[
            Step(id=s["id"], text=s["text"], image=s.get("image"),
                 image_suggested=bool(s.get("image_suggested", False)))
            for s in entry.get("steps") or []
        ],
    )


class MissionList:
    """Missions kept in one list of config.yaml (its `section`), found by id."""

    section = "missions"

    def __init__(self, store: ConfigStore):
        self._store = store

    def atomic(self):
        """Group several calls so they are read and saved as one change."""
        return self._store.edit()

    def _all(self) -> list[Mission]:
        return [_from_doc(entry) for entry in self._store.load()[self.section]]

    def get(self, mission_id: str) -> Mission | None:
        return next((m for m in self._all() if m.id == mission_id), None)

    def add(self, mission: Mission) -> None:
        with self._store.edit() as doc:
            doc[self.section].append(_to_doc(mission))

    def update(self, mission: Mission) -> None:
        with self._store.edit() as doc:
            doc[self.section] = [
                _to_doc(mission) if entry["id"] == mission.id else entry for entry in doc[self.section]
            ]

    def remove(self, mission_id: str) -> None:
        with self._store.edit() as doc:
            doc[self.section] = [entry for entry in doc[self.section] if entry["id"] != mission_id]


class MissionsRepository(MissionList):
    """The children's missions."""

    def list_for_child(self, child_id: str) -> list[Mission]:
        return [m for m in self._all() if m.child_id == child_id]

    def remove_for_child(self, child_id: str) -> list[Mission]:
        with self._store.edit() as doc:
            removed = [_from_doc(e) for e in doc["missions"] if e["child_id"] == child_id]
            doc["missions"] = [e for e in doc["missions"] if e["child_id"] != child_id]
        return removed

    def reorder_child(self, child_id: str, mission_ids: list[str]) -> None:
        """Put the child's missions in the given order, leaving other children's in place."""
        with self._store.edit() as doc:
            by_id = {e["id"]: e for e in doc["missions"] if e["child_id"] == child_id}
            ordered = iter([by_id[mission_id] for mission_id in mission_ids])
            doc["missions"] = [
                next(ordered) if e["child_id"] == child_id else e for e in doc["missions"]
            ]
