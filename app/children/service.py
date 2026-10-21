import secrets
from dataclasses import dataclass, replace
from pathlib import Path

from app.children import avatars
from app.children.repository import Child, ChildrenRepository
from app.errors import ConflictError, InvalidError, NotFoundError, TooLargeError, UnsupportedTypeError
from app.storage.photo_store import PhotoStore

MAX_PHOTO_BYTES = 5 * 1024 * 1024
PHOTO_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


@dataclass
class ChildData:
    """What a parent fills in when adding or editing a child."""

    name: str
    avatar_type: str
    preset: str | None = None
    color: str | None = None


def sniff_photo_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


class ChildrenService:
    def __init__(self, children: ChildrenRepository, photos: PhotoStore):
        self._children = children
        self._photos = photos

    def list(self) -> list[Child]:
        return self._children.list()

    def get(self, child_id: str) -> Child:
        child = self._children.get(child_id)
        if child is None:
            raise NotFoundError("Child not found")
        return child

    def create(self, data: ChildData) -> Child:
        with self._children.atomic():
            preset, color = self._resolve_avatar(data, child_id=None)
            child = Child(
                id=secrets.token_hex(4),
                name=data.name,
                avatar_type=data.avatar_type,
                preset=preset,
                photo=None,
                color=color,
            )
            self._children.add(child)
        return child

    def update(self, child_id: str, data: ChildData) -> Child:
        with self._children.atomic():
            old = self.get(child_id)
            preset, color = self._resolve_avatar(data, child_id=child_id)
            child = replace(
                old,
                name=data.name,
                avatar_type=data.avatar_type,
                preset=preset,
                photo=old.photo if data.avatar_type == "photo" else None,
                color=color,
            )
            self._children.update(child)
        if child.photo is None:
            self._photos.delete(old.photo)
        return child

    def delete(self, child_id: str) -> None:
        # Only the config entry and avatar go away; history in SQLite (when it exists) stays.
        with self._children.atomic():
            child = self.get(child_id)
            self._children.remove(child_id)
        self._photos.delete(child.photo)

    def set_photo(self, child_id: str, data: bytes, media_type: str) -> Child:
        if media_type not in PHOTO_TYPES:
            raise UnsupportedTypeError("Photo must be JPEG, PNG or WebP")
        if len(data) > MAX_PHOTO_BYTES:
            raise TooLargeError("Photo is too large (max 5 MB)")
        if sniff_photo_type(data) != media_type:
            raise InvalidError("File content does not match its type")

        with self._children.atomic():
            old = self.get(child_id)
            filename = self._photos.save(data, prefix=child_id, extension=PHOTO_TYPES[media_type])
            child = replace(old, avatar_type="photo", preset=None, photo=filename)
            self._children.update(child)
        self._photos.delete(old.photo)
        return child

    def photo_path(self, child_id: str) -> Path:
        child = self.get(child_id)
        if not child.photo:
            raise NotFoundError("Child has no photo")
        path = self._photos.path(child.photo)
        if path is None:
            raise NotFoundError("Photo file missing")
        return path

    def _resolve_avatar(self, data: ChildData, child_id: str | None) -> tuple[str | None, str]:
        """Validate the avatar choice and return (preset, color).

        A preset is exclusive to one child and always brings its own color.
        Photo avatars pick any palette color; colors may repeat.
        """
        if data.avatar_type == "photo":
            if data.color not in avatars.PALETTE_COLORS:
                raise InvalidError("Color must come from the palette")
            return None, data.color

        preset = avatars.PRESETS_BY_ID.get(data.preset or "")
        if preset is None:
            raise InvalidError("Unknown preset")
        if any(c.preset == preset["id"] and c.id != child_id for c in self._children.list()):
            raise ConflictError("Preset already in use")
        return preset["id"], preset["color"]
