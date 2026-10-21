"""Rules for photos uploaded by the parents (avatars, missions, steps)."""

import re

from app.errors import InvalidError, TooLargeError, UnsupportedTypeError

MAX_PHOTO_BYTES = 5 * 1024 * 1024
PHOTO_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
PHOTO_FILENAME = re.compile(r"^[a-z0-9-]+\.(jpg|png|webp)$")


def sniff_photo_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_photo(data: bytes, media_type: str) -> str:
    """Check an upload and return the file extension to store it with."""
    if media_type not in PHOTO_TYPES:
        raise UnsupportedTypeError("Photo must be JPEG, PNG or WebP")
    if len(data) > MAX_PHOTO_BYTES:
        raise TooLargeError("Photo is too large (max 5 MB)")
    if sniff_photo_type(data) != media_type:
        raise InvalidError("File content does not match its type")
    return PHOTO_TYPES[media_type]
