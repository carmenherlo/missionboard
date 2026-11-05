"""Image libraries (e.g. Fluent Emoji) and image references.

An image reference is a short string saved in config.yaml:
- "fluent/toothbrush": image "toothbrush" of the library "fluent";
- "photo/ab12cd34-9f8e7d6c.jpg": a photo uploaded by the parents.

Each library is a folder under static/libraries/ with its SVGs, a
catalog.json (names and keywords for the search) and its licenses.
To add or remove a library, change only LIBRARIES below.
"""

import json
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from app.images import suggest

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
PHOTO_SOURCE = "photo"


@dataclass(frozen=True)
class Library:
    id: str
    directory: Path
    base_url: str

    @cached_property
    def catalog(self) -> dict:
        return json.loads((self.directory / "catalog.json").read_text(encoding="utf-8"))

    @cached_property
    def item_ids(self) -> frozenset[str]:
        return frozenset(item["id"] for item in self.catalog["items"])

    @cached_property
    def featured_words(self) -> list[tuple[str, set[str]]]:
        """(ref, words of its name and keywords) for every featured image, in order."""
        items = {item["id"]: item for item in self.catalog["items"]}
        result, seen = [], set()
        for theme in self.catalog.get("featured", []):
            for item_id in theme["items"]:
                if item_id in seen or item_id not in items:
                    continue
                seen.add(item_id)
                item = items[item_id]
                text = " ".join([item["name"], *item["keywords"]])
                result.append((f"{self.id}/{item_id}", set(suggest.words(text))))
        return result


LIBRARIES = [
    Library("fluent", STATIC_DIR / "libraries" / "fluent", "static/libraries/fluent"),
]


def split_ref(ref: str) -> tuple[str, str]:
    source, _, name = ref.partition("/")
    return source, name


def photo_ref(filename: str) -> str:
    return f"{PHOTO_SOURCE}/{filename}"


def photo_filename(ref: str | None) -> str | None:
    """The uploaded file behind a reference, or None if it is not a photo."""
    if not ref:
        return None
    source, name = split_ref(ref)
    return name if source == PHOTO_SOURCE else None


class ImageLibraries:
    def __init__(self, libraries: list[Library]):
        self._by_id = {library.id: library for library in libraries}

    def catalogs(self) -> list[dict]:
        return [
            {**library.catalog, "base_url": library.base_url} for library in self._by_id.values()
        ]

    def suggest(self, text: str) -> str | None:
        """An image for this text among the featured ones, or None."""
        candidates = [c for library in self._by_id.values() for c in library.featured_words]
        return suggest.best_match(text, candidates)

    def exists(self, ref: str) -> bool:
        source, name = split_ref(ref)
        library = self._by_id.get(source)
        return library is not None and name in library.item_ids

    def url(self, ref: str | None) -> str | None:
        """Where the browser loads the image; None if it no longer exists."""
        if not ref:
            return None
        if filename := photo_filename(ref):
            return f"api/photos/{filename}"
        if not self.exists(ref):
            return None  # e.g. a library that was removed: the step shows its text only
        source, name = split_ref(ref)
        return f"{self._by_id[source].base_url}/{name}.svg"
