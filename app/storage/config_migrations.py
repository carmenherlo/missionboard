"""Versioned upgrades of config.yaml.

Each migration takes the document at version N and returns it at N + 1, and is
frozen: it hardcodes the values of its time. They start at FIRST_VERSION: files
older than that are not converted (see fresh_start.py).
"""

import copy
from collections.abc import Callable

FIRST_VERSION = 16  # family missions: mission → task → step
CURRENT_VERSION = 19


class ConfigVersionError(Exception):
    """The file was written by a newer version of the app."""


class ConfigTooOldError(Exception):
    """The file is from before FIRST_VERSION (a copy of then, being put back)."""


_MIGRATIONS: dict[int, Callable[[dict], dict]] = {}


def _hhmm(minute: int) -> str:
    minute %= 24 * 60
    return f"{minute // 60:02d}:{minute % 60:02d}"


def _minutes(value) -> int:
    if isinstance(value, int):  # YAML 1.1 read an unquoted 7:30 as 450
        return value
    return int(value[:2]) * 60 + int(value[3:])


def _v16_to_v17(doc: dict) -> dict:
    """Seasons: the start of each moment (morning, day, evening, night) instead of the
    sunrise and the sunset with a margin around them; the margin goes away."""
    settings = doc.get("settings") or {}
    margin = settings.pop("moment_margin_minutes", 120)
    seasons = []
    for season in settings.get("seasons") or []:
        if "sunrise" not in season:
            seasons.append(season)
            continue
        sunrise, sunset = _minutes(season["sunrise"]), _minutes(season["sunset"])
        seasons.append({"name": season["name"], "start": season["start"],
                        "manana": _hhmm(sunrise - margin), "dia": _hhmm(sunrise + margin),
                        "tarde": _hhmm(sunset - margin), "noche": _hhmm(sunset + margin)})
    if seasons:
        settings["seasons"] = seasons
    doc["settings"] = settings
    doc["version"] = 17
    return doc


_MIGRATIONS[16] = _v16_to_v17


def _v17_to_v18(doc: dict) -> dict:
    """The family's own avatars (avatares.html): an empty list to start with."""
    doc.setdefault("avatars", [])
    doc["version"] = 18
    return doc


_MIGRATIONS[17] = _v17_to_v18


def _v18_to_v19(doc: dict) -> dict:
    """The home's reflection on opening, off: too much (12/11). It can be switched on again in Ajustes."""
    home = (doc.get("settings") or {}).get("home")
    if isinstance(home, dict):
        home["shine"] = False
    doc["version"] = 19
    return doc


_MIGRATIONS[18] = _v18_to_v19


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
        "avatars": [],
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
