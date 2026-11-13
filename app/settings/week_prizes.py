"""The pictures of the week's prizes (rachas.html, 13/11): the big one and the smaller one.

Like a prize's picture: a library image is a reference ("fluent/kite"); a photo is only
set by uploading it, and its file goes away when it is replaced. They live in
settings.streak_week (prize_image, second_image).
"""

from typing import Literal

from app.images.libraries import ImageLibraries, photo_ref
from app.images.photos import validate_photo
from app.images.rules import ImageRules
from app.settings.service import SettingsService
from app.storage.photo_store import PhotoStore

Which = Literal["prize", "second"]


class WeekPrizeImages:
    def __init__(self, settings: SettingsService, libraries: ImageLibraries, photos: PhotoStore):
        self._settings = settings
        self._libraries = libraries
        self._photos = photos
        self._images = ImageRules(libraries, photos)

    def view(self) -> dict:
        week = self._settings.settings().streak_week
        return {which: self._one(getattr(week, f"{which}_image")) for which in ("prize", "second")}

    def set_image(self, which: Which, image: str | None) -> dict:
        old = getattr(self._settings.settings().streak_week, f"{which}_image")
        return self._save(which, old, self._images.check_new_image(old, image))

    def set_photo(self, which: Which, data: bytes, media_type: str) -> dict:
        extension = validate_photo(data, media_type)
        old = getattr(self._settings.settings().streak_week, f"{which}_image")
        filename = self._photos.save(data, prefix=f"week-{which}", extension=extension)
        return self._save(which, old, photo_ref(filename))

    def _save(self, which: Which, old: str | None, new: str | None) -> dict:
        week = self._settings.settings().streak_week
        self._settings.update_settings({"streak_week": week.model_copy(update={f"{which}_image": new})})
        self._images.drop_replaced_photo(old, new)
        return self.view()

    def _one(self, ref: str | None) -> dict:
        return {"ref": ref, "url": self._libraries.url(ref)}
