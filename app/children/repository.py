from dataclasses import asdict, dataclass, fields

from app.storage.config_store import ConfigStore


@dataclass
class Child:
    id: str
    name: str
    preset: str | None
    color: str


_FIELDS = [f.name for f in fields(Child)]


def _from_doc(entry: dict) -> Child:
    return Child(**{name: entry.get(name) for name in _FIELDS})


class ChildrenRepository:
    def __init__(self, store: ConfigStore):
        self._store = store

    def atomic(self):
        """Group several calls so they are read and saved as one change."""
        return self._store.edit()

    def list(self) -> list[Child]:
        return [_from_doc(entry) for entry in self._store.load()["children"]]

    def get(self, child_id: str) -> Child | None:
        return next((c for c in self.list() if c.id == child_id), None)

    def add(self, child: Child) -> None:
        with self._store.edit() as doc:
            doc["children"].append(asdict(child))

    def update(self, child: Child) -> None:
        with self._store.edit() as doc:
            doc["children"] = [
                asdict(child) if entry["id"] == child.id else entry for entry in doc["children"]
            ]

    def remove(self, child_id: str) -> None:
        with self._store.edit() as doc:
            doc["children"] = [entry for entry in doc["children"] if entry["id"] != child_id]
