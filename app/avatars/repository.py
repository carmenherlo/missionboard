"""The family's own avatars (avatares.html, 11/11): the `avatars` list of config.yaml,
and their pictures in data/avatars/. The app's animals are in app/children/avatars.py."""

import secrets
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from app.storage.config_store import ConfigStore

AVATARS_DIRNAME = "avatars"
ID_PREFIX = "family-"  # never the same as an app animal's id


@dataclass
class FamilyAvatar:
    id: str
    name: str
    image: str  # the file, in data/avatars/
    color: str  # #rrggbb: any colour, its tones are worked out
    color_suggested: bool  # the one taken from the picture: changing the picture changes it


_FIELDS = [f.name for f in fields(FamilyAvatar)]


class AvatarsRepository:
    def __init__(self, store: ConfigStore):
        self._store = store

    def atomic(self):
        return self._store.edit()

    def list(self) -> list[FamilyAvatar]:
        return [FamilyAvatar(**{k: e.get(k) for k in _FIELDS}) for e in self._store.load().get("avatars") or []]

    def get(self, avatar_id: str) -> FamilyAvatar | None:
        return next((a for a in self.list() if a.id == avatar_id), None)

    def add(self, avatar: FamilyAvatar) -> None:
        with self._store.edit() as doc:
            doc.setdefault("avatars", []).append(asdict(avatar))

    def update(self, avatar: FamilyAvatar) -> None:
        with self._store.edit() as doc:
            doc["avatars"] = [asdict(avatar) if e["id"] == avatar.id else e for e in doc["avatars"]]

    def remove(self, avatar_id: str) -> None:
        with self._store.edit() as doc:
            doc["avatars"] = [e for e in doc["avatars"] if e["id"] != avatar_id]


def new_id() -> str:
    return f"{ID_PREFIX}{secrets.token_hex(4)}"


class AvatarFiles:
    """The pictures, in data/avatars/, with names the app gives them."""

    def __init__(self, data_dir: Path):
        self.directory = data_dir / AVATARS_DIRNAME

    def save(self, data: bytes, extension: str) -> str:
        self.directory.mkdir(parents=True, exist_ok=True)
        filename = f"{secrets.token_hex(6)}{extension}"
        (self.directory / filename).write_bytes(data)
        return filename

    def delete(self, filename: str | None) -> None:
        if filename:
            (self.directory / filename).unlink(missing_ok=True)

    def path(self, filename: str) -> Path | None:
        path = self.directory / filename
        return path if path.is_file() else None
