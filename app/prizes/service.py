import secrets
from dataclasses import replace
from types import SimpleNamespace

from app.errors import NotFoundError
from app.events.service import EventLog
from app.images.libraries import ImageLibraries, photo_filename, photo_ref
from app.images.photos import validate_photo
from app.images.rules import ImageRules
from app.prizes.repository import Prize, PrizesRepository
from app.storage.photo_store import PhotoStore

UNSET = object()


class PrizesService:
    """The list of daily prizes, edited like the steps of a mission."""

    def __init__(self, prizes: PrizesRepository, libraries: ImageLibraries, photos: PhotoStore, events: EventLog):
        self._prizes = prizes
        self._photos = photos
        self._images = ImageRules(libraries, photos)
        self._events = events

    def list(self) -> list[Prize]:
        return self._prizes.list()

    def get(self, prize_id: str) -> Prize:
        prize = self._prizes.get(prize_id)
        if prize is None:
            raise NotFoundError("Prize not found")
        return prize

    def create(self, text: str) -> Prize:
        image, suggested = self._images.suggest(text)
        prize = Prize(id=secrets.token_hex(4), text=text, image=image, image_suggested=suggested)
        self._prizes.add(prize)
        self._log("created", prize)
        return prize

    def update(self, prize_id: str, *, text=UNSET, image=UNSET) -> Prize:
        with self._prizes.atomic():
            old = self.get(prize_id)
            prize = replace(old)
            if text is not UNSET:
                prize.text = text
            if image is not UNSET:
                prize.image = self._images.check_new_image(old.image, image)
                prize.image_suggested = False
            self._prizes.update(prize)
        self._images.drop_replaced_photo(old.image, prize.image)
        changes = {
            ("name" if field == "text" else field): getattr(prize, field)
            for field in ("text", "image")
            if getattr(prize, field) != getattr(old, field)
        }
        if changes:
            self._log("changed", prize, changes)
        return prize

    def set_photo(self, prize_id: str, data: bytes, media_type: str) -> Prize:
        extension = validate_photo(data, media_type)
        with self._prizes.atomic():
            old = self.get(prize_id)
            filename = self._photos.save(data, prefix=prize_id, extension=extension)
            prize = replace(old, image=photo_ref(filename), image_suggested=False)
            self._prizes.update(prize)
        self._images.drop_replaced_photo(old.image, prize.image)
        self._log("changed", prize, {"image": prize.image})
        return prize

    def delete(self, prize_id: str) -> None:
        with self._prizes.atomic():
            prize = self.get(prize_id)
            self._prizes.remove(prize_id)
        self._photos.delete(photo_filename(prize.image))
        self._log("deleted", prize)

    def _log(self, action: str, prize: Prize, changes: dict | None = None) -> None:
        # The log keeps names: a prize goes in the mission columns, as "what".
        named = SimpleNamespace(id=prize.id, name=prize.text)
        self._events.config_changed("prize", action, mission=named, changes=changes)
