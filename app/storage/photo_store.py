"""Uploaded images, stored as files in data/photos/."""

import secrets
from pathlib import Path

PHOTOS_DIRNAME = "photos"


class PhotoStore:
    def __init__(self, data_dir: Path):
        self.directory = data_dir / PHOTOS_DIRNAME

    def save(self, data: bytes, prefix: str, extension: str) -> str:
        """Store the image under a new unique name and return that name."""
        self.directory.mkdir(parents=True, exist_ok=True)
        filename = f"{prefix}-{secrets.token_hex(4)}{extension}"
        (self.directory / filename).write_bytes(data)
        return filename

    def delete(self, filename: str | None) -> None:
        if filename:
            (self.directory / filename).unlink(missing_ok=True)

    def path(self, filename: str) -> Path | None:
        path = self.directory / filename
        return path if path.is_file() else None
