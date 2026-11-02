from app.errors import InvalidError
from app.images.libraries import ImageLibraries, photo_filename
from app.storage.photo_store import PhotoStore


class ImageRules:
    """How anything with a picture (mission, step, prize) gets and changes it.

    A library image is a reference ("fluent/rocket"); a photo is only set by
    uploading it, and its file goes away when it is replaced.
    """

    def __init__(self, libraries: ImageLibraries, photos: PhotoStore):
        self._libraries = libraries
        self._photos = photos

    def suggest(self, text: str) -> tuple[str | None, bool]:
        """An image picked from the text, marked as suggested; (None, False) if none fits."""
        ref = self._libraries.suggest(text)
        return ref, ref is not None

    def check_library_image(self, image: str | None) -> str | None:
        if image is not None and not self._libraries.exists(image):
            raise InvalidError("Unknown image")
        return image

    def check_new_image(self, current: str | None, image: str | None) -> str | None:
        # Photos are set by uploading; keeping the current one is the only other way to name one.
        if image is not None and image == current:
            return image
        return self.check_library_image(image)

    def drop_replaced_photo(self, old: str | None, new: str | None) -> None:
        if old != new:
            self._photos.delete(photo_filename(old))
