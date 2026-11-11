from dataclasses import replace
from types import SimpleNamespace

from app.avatars.repository import AvatarFiles, AvatarsRepository, FamilyAvatar, new_id
from app.children.avatars import HEX_COLOR
from app.children.repository import ChildrenRepository
from app.errors import ConflictError, InvalidError, NotFoundError, TooLargeError, UnsupportedTypeError
from app.events.service import EventLog
from app.images.photos import sniff_photo_type

MAX_AVATAR_BYTES = 2 * 1024 * 1024
# With a transparent background, so the picture floats in its ring like the animals.
AVATAR_TYPES = {"image/png": ".png", "image/webp": ".webp"}


def check_picture(data: bytes) -> str:
    """The file extension for an avatar's picture, by its content."""
    if len(data) > MAX_AVATAR_BYTES:
        raise TooLargeError("The picture is too large (max 2 MB)")
    extension = AVATAR_TYPES.get(sniff_photo_type(data) or "")
    if extension is None:
        raise UnsupportedTypeError("An avatar must be PNG or WebP")
    return extension


def check_color(color: str) -> str:
    color = color.lower()
    if not HEX_COLOR.match(color):
        raise InvalidError("A colour is #rrggbb")
    return color


class AvatarsService:
    """The family's avatars: uploaded here, worn by one child each. The colour of a
    child's ring comes from their avatar, so changing it changes theirs."""

    def __init__(self, avatars: AvatarsRepository, files: AvatarFiles, children: ChildrenRepository, events: EventLog):
        self._avatars = avatars
        self._files = files
        self._children = children
        self._events = events

    def list(self) -> list[FamilyAvatar]:
        return self._avatars.list()

    def get(self, avatar_id: str) -> FamilyAvatar:
        avatar = self._avatars.get(avatar_id)
        if avatar is None:
            raise NotFoundError("Avatar not found")
        return avatar

    def worn_by(self, avatar_id: str) -> list:
        return [c for c in self._children.list() if c.preset == avatar_id]

    def upload(self, data: bytes, name: str, color: str, suggested: bool) -> FamilyAvatar:
        extension = check_picture(data)
        color = check_color(color)
        avatar = FamilyAvatar(id=new_id(), name=name, image=self._files.save(data, extension),
                              color=color, color_suggested=suggested)
        self._avatars.add(avatar)
        self._log("created", avatar)
        return avatar

    def update(self, avatar_id: str, *, name: str | None = None, color: str | None = None,
               suggested: bool | None = None) -> FamilyAvatar:
        with self._avatars.atomic():
            old = self.get(avatar_id)
            avatar = replace(old, name=name if name is not None else old.name,
                             color=check_color(color) if color is not None else old.color,
                             color_suggested=suggested if suggested is not None else old.color_suggested)
            self._avatars.update(avatar)
            self._recolour(avatar)
        changes = {key: getattr(avatar, key) for key in ("name", "color") if getattr(avatar, key) != getattr(old, key)}
        if changes:
            self._log("changed", avatar, changes)
        return avatar

    def set_picture(self, avatar_id: str, data: bytes, suggested_color: str | None) -> FamilyAvatar:
        """A new picture; its colour too, if the one there was the one suggested by the old picture."""
        extension = check_picture(data)
        with self._avatars.atomic():
            old = self.get(avatar_id)
            color = check_color(suggested_color) if suggested_color and old.color_suggested else old.color
            avatar = replace(old, image=self._files.save(data, extension), color=color)
            self._avatars.update(avatar)
            self._recolour(avatar)
        self._files.delete(old.image)
        self._log("changed", avatar, {"image": "photo/"})
        return avatar

    def delete(self, avatar_id: str) -> None:
        """Only one nobody wears: nobody is left with an avatar they did not choose."""
        with self._avatars.atomic():
            avatar = self.get(avatar_id)
            if self.worn_by(avatar_id):
                raise ConflictError("A child wears this avatar")
            self._avatars.remove(avatar_id)
        self._files.delete(avatar.image)
        self._log("deleted", avatar)

    def file(self, avatar_id: str):
        path = self._files.path(self.get(avatar_id).image)
        if path is None:
            raise NotFoundError("Avatar picture not found")
        return path

    def _recolour(self, avatar: FamilyAvatar) -> None:
        for child in self.worn_by(avatar.id):
            if child.color != avatar.color:
                self._children.update(replace(child, color=avatar.color))

    def _log(self, action: str, avatar: FamilyAvatar, changes: dict | None = None) -> None:
        self._events.config_changed("avatar", action, mission=SimpleNamespace(id=avatar.id, name=avatar.name),
                                    changes=changes)
