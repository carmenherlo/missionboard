import secrets
from dataclasses import dataclass, replace
from pathlib import Path
from collections.abc import Iterable
from typing import Protocol

from app.children import avatars
from app.children.repository import Child, ChildrenRepository
from app.errors import ConflictError, InvalidError, NotFoundError
from app.images.photos import validate_photo
from app.storage.photo_store import PhotoStore


@dataclass
class ChildData:
    """What a parent fills in when adding or editing a child."""

    name: str
    avatar_type: str
    preset: str | None = None
    color: str | None = None


class ChildDependent(Protocol):
    """Configuration that belongs to a child (e.g. missions) and goes away with it."""

    def remove_child_data(self, child_id: str) -> list[str]:
        """Remove the child's entries and return the photo files they used."""
        ...


class ChildrenService:
    def __init__(
        self,
        children: ChildrenRepository,
        photos: PhotoStore,
        dependents: Iterable[ChildDependent] = (),
    ):
        self._children = children
        self._photos = photos
        self._dependents = list(dependents)

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
        # The child's configuration (entry, missions...) and photos go away;
        # history in SQLite (when it exists) stays.
        with self._children.atomic():
            child = self.get(child_id)
            self._children.remove(child_id)
            photos = [child.photo]
            for dependent in self._dependents:
                photos += dependent.remove_child_data(child_id)
        for filename in photos:
            self._photos.delete(filename)

    def set_photo(self, child_id: str, data: bytes, media_type: str) -> Child:
        extension = validate_photo(data, media_type)
        with self._children.atomic():
            old = self.get(child_id)
            filename = self._photos.save(data, prefix=child_id, extension=extension)
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
