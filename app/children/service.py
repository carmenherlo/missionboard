import secrets
from dataclasses import dataclass, replace
from collections.abc import Callable, Iterable
from typing import Protocol

from app.avatars.repository import AvatarsRepository
from app.children import avatars
from app.children.repository import Child, ChildrenRepository
from app.errors import ConflictError, InvalidError, NotFoundError
from app.events.service import EventLog
from app.storage.photo_store import PhotoStore


@dataclass
class ChildData:
    """What a parent fills in when adding or editing a child."""

    name: str
    preset: str


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
        events: EventLog,
        dependents: Iterable[ChildDependent] = (),
        welcome: Callable[[Child], None] = lambda child: None,
        family_avatars: AvatarsRepository | None = None,
    ):
        self._children = children
        self._photos = photos
        self._events = events
        self._dependents = list(dependents)
        self._welcome = welcome  # what a new child starts with (their first stars)
        self._family_avatars = family_avatars  # the family's own, besides the app's animals

    def list(self) -> list[Child]:
        return self._children.list()

    def get(self, child_id: str) -> Child:
        child = self._children.get(child_id)
        if child is None:
            raise NotFoundError("Child not found")
        return child

    def create(self, data: ChildData) -> Child:
        with self._children.atomic():
            preset = self._check_preset(data.preset, child_id=None)
            child = Child(id=secrets.token_hex(4), name=data.name, preset=preset["id"], color=preset["color"])
            self._children.add(child)
        self._welcome(child)
        self._events.config_changed("child", "created", child=child)
        return child

    def update(self, child_id: str, data: ChildData) -> Child:
        with self._children.atomic():
            old = self.get(child_id)
            preset = self._check_preset(data.preset, child_id=child_id)
            child = replace(old, name=data.name, preset=preset["id"], color=preset["color"])
            self._children.update(child)
        changes = {}
        if child.name != old.name:
            changes["name"] = child.name
        if child.preset != old.preset:
            changes["avatar"] = self._avatar_label(child.preset)
        if changes:
            self._events.config_changed("child", "changed", child=child, changes=changes)
        return child

    def delete(self, child_id: str) -> None:
        # The child's configuration (entry, missions...) goes away; history in SQLite stays.
        with self._children.atomic():
            child = self.get(child_id)
            self._children.remove(child_id)
            photos = []
            for dependent in self._dependents:
                photos += dependent.remove_child_data(child_id)
        for filename in photos:
            self._photos.delete(filename)
        self._events.config_changed("child", "deleted", child=child)

    def _find_avatar(self, avatar_id: str) -> dict | None:
        """An app animal or one of the family's: its id, name and colour."""
        preset = avatars.PRESETS_BY_ID.get(avatar_id or "")
        if preset is not None:
            return preset
        family = self._family_avatars.get(avatar_id) if self._family_avatars and avatar_id else None
        return {"id": family.id, "label": family.name, "color": family.color} if family else None

    def _avatar_label(self, avatar_id: str | None) -> str:
        """How the event log names an avatar: the animal, or the family's avatar's name."""
        found = self._find_avatar(avatar_id or "")
        return found["label"].lower() if found else "—"

    def _check_preset(self, preset_id: str, child_id: str | None) -> dict:
        """An existing avatar, exclusive to one child. It brings the colour of their ring."""
        preset = self._find_avatar(preset_id)
        if preset is None:
            raise InvalidError("Unknown preset")
        if any(c.preset == preset["id"] and c.id != child_id for c in self._children.list()):
            raise ConflictError("Preset already in use")
        return preset
