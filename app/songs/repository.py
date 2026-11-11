"""The family's songs (rutinas-4, section 3): the `songs` list of config.yaml, and
their files in data/sounds/ (the family's, like the photos; the examples bring two, see app/samples.py)."""

import secrets
from dataclasses import asdict, dataclass
from pathlib import Path

from app.storage.config_store import ConfigStore

SOUNDS_DIRNAME = "sounds"


@dataclass
class Song:
    id: str
    name: str
    file: str  # in data/sounds/
    seconds: float  # how long it lasts (measured by the browser that uploaded it)


class SongsRepository:
    def __init__(self, store: ConfigStore):
        self._store = store

    def atomic(self):
        return self._store.edit()

    def list(self) -> list[Song]:
        return [Song(**{k: e[k] for k in ("id", "name", "file", "seconds")}) for e in self._store.load().get("songs") or []]

    def get(self, song_id: str) -> Song | None:
        return next((s for s in self.list() if s.id == song_id), None)

    def add(self, song: Song) -> None:
        with self._store.edit() as doc:
            doc.setdefault("songs", []).append(asdict(song))

    def update(self, song: Song) -> None:
        with self._store.edit() as doc:
            doc["songs"] = [asdict(song) if e["id"] == song.id else e for e in doc["songs"]]

    def remove(self, song_id: str) -> None:
        with self._store.edit() as doc:
            doc["songs"] = [e for e in doc["songs"] if e["id"] != song_id]


class SoundFiles:
    """The song files, in data/sounds/."""

    def __init__(self, data_dir: Path):
        self.directory = data_dir / SOUNDS_DIRNAME

    def save(self, data: bytes, extension: str) -> str:
        self.directory.mkdir(parents=True, exist_ok=True)
        filename = f"{secrets.token_hex(6)}{extension}"
        (self.directory / filename).write_bytes(data)
        return filename

    def delete(self, filename: str) -> None:
        (self.directory / filename).unlink(missing_ok=True)

    def path(self, filename: str) -> Path | None:
        path = self.directory / filename
        return path if path.is_file() else None
