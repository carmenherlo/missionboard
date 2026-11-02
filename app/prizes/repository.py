from dataclasses import asdict, dataclass

from app.storage.config_store import ConfigStore


@dataclass
class Prize:
    """A daily prize: something the family does, not stars ("Elegir la cena")."""

    id: str
    text: str
    image: str | None = None
    image_suggested: bool = False


def _from_doc(entry: dict) -> Prize:
    return Prize(
        id=entry["id"],
        text=entry["text"],
        image=entry.get("image"),
        image_suggested=bool(entry.get("image_suggested", False)),
    )


class PrizesRepository:
    """The `prizes` list of config.yaml, the same for every child."""

    def __init__(self, store: ConfigStore):
        self._store = store

    def atomic(self):
        return self._store.edit()

    def list(self) -> list[Prize]:
        return [_from_doc(entry) for entry in self._store.load().get("prizes") or []]

    def get(self, prize_id: str) -> Prize | None:
        return next((p for p in self.list() if p.id == prize_id), None)

    def add(self, prize: Prize) -> None:
        with self._store.edit() as doc:
            doc.setdefault("prizes", []).append(asdict(prize))

    def update(self, prize: Prize) -> None:
        with self._store.edit() as doc:
            doc["prizes"] = [asdict(prize) if e["id"] == prize.id else e for e in doc["prizes"]]

    def remove(self, prize_id: str) -> None:
        with self._store.edit() as doc:
            doc["prizes"] = [e for e in doc["prizes"] if e["id"] != prize_id]
