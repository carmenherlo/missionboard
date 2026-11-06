"""Versioned upgrades of config.yaml.

Each migration takes the document at version N and returns it at N + 1, and is
frozen: it hardcodes the values of its time. They start at FIRST_VERSION: files
older than that are not converted (see fresh_start.py).
"""

import copy
from collections.abc import Callable

FIRST_VERSION = 16  # family missions: mission → task → step
CURRENT_VERSION = 16


class ConfigVersionError(Exception):
    """The file was written by a newer version of the app."""


class ConfigTooOldError(Exception):
    """The file is from before FIRST_VERSION (a copy of then, being put back)."""


_MIGRATIONS: dict[int, Callable[[dict], dict]] = {}


def upgrade(doc: dict) -> dict:
    """Return the document at CURRENT_VERSION. The input is not modified."""
    version = doc.get("version", 1)
    if version > CURRENT_VERSION:
        raise ConfigVersionError(
            f"config.yaml is version {version}; this app understands up to {CURRENT_VERSION}"
        )
    if version < FIRST_VERSION:
        raise ConfigTooOldError(f"config.yaml is version {version}, from before family missions")
    doc = {**initial(), **copy.deepcopy(doc)}  # keys missing from a hand-written file
    while version < CURRENT_VERSION:
        doc = _MIGRATIONS[version](doc)
        version += 1
    return doc


def initial() -> dict:
    """The document used when there is no config.yaml yet."""
    return {
        "version": CURRENT_VERSION,
        "parents": {"code": "1234"},
        "children": [],
        "settings": {"stars_per_mission": 1, "daily_prize_spins": 1, "day_starts_at": "00:00"},
        "features": {"daily_prize": True, "shop": True, "streaks": True, "dashboard": True, "routines": True,
                     "games": False},
        "missions": [],
        "routines": [],
        "songs": [],
        "prizes": [
            {"id": "guerra-de-cojines", "text": "Guerra de cojines", "image": None, "image_suggested": False},
            {"id": "elegir-la-cena", "text": "Elegir la cena", "image": "fluent/pizza", "image_suggested": False},
            {"id": "un-cuento-mas", "text": "Un cuento más", "image": "fluent/open-book", "image_suggested": False},
            {"id": "mas-juego", "text": "15 minutos más de juego", "image": "fluent/joystick", "image_suggested": False},
        ],
        "shop": [
            {"id": "elegir-postre", "text": "Elegir el postre", "image": "fluent/ice-cream", "image_suggested": False,
             "price": 3},
            {"id": "globo", "text": "Un globo", "image": "fluent/balloon", "image_suggested": False, "price": 5},
            {"id": "peluche", "text": "Un peluche", "image": "fluent/teddy-bear", "image_suggested": False, "price": 20},
        ],
    }
