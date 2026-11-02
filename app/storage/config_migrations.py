"""Versioned upgrades of config.yaml.

Each migration takes the document at version N and returns it at N + 1.
Migrations are frozen: they hardcode the values of their time and never
import live defaults, so they keep producing the same result forever.
"""

import copy

CURRENT_VERSION = 4


class ConfigVersionError(Exception):
    """The file was written by a newer version of the app."""


# Shape of a version 1 file; fills keys missing from hand-written or old files.
_V1_BASE = {
    "version": 1,
    "parents": {"code": "1234"},
    "children": [],
}


def _v1_to_v2(doc: dict) -> dict:
    """Add the settings and features sections, so they can be tuned by hand."""
    return {
        **doc,
        "version": 2,
        "settings": {
            "stars_per_mission": 1,
            "daily_prize_spins": 1,
            "day_starts_at": "00:00",
            **(doc.get("settings") or {}),
        },
        "features": {
            "daily_prize": True,
            "shop": True,
            "streaks": True,
            "dashboard": True,
            "routines": True,
            "games": False,
            **(doc.get("features") or {}),
        },
    }


def _v2_to_v3(doc: dict) -> dict:
    """Add the missions list (each mission belongs to one child)."""
    return {**doc, "version": 3, "missions": doc.get("missions") or []}


def _sample_template(id: str, name: str, image: str, days: list[str], steps: list[tuple]) -> dict:
    return {
        "id": id,
        "name": name,
        "image": image,
        "image_suggested": False,
        "days": days,
        "schedule": None,
        "steps": [
            {"id": f"{id}-{n}", "text": text, "image": step_image, "image_suggested": False}
            for n, (text, step_image) in enumerate(steps, start=1)
        ],
    }


_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]
_ALL_DAYS = _WEEKDAYS + ["sat", "sun"]

# Fixed ids: a fresh install builds this document on every read until the
# first save, so random ids would change between two requests.
_SAMPLE_TEMPLATES = [
    _sample_template("despegue", "Despegue", "fluent/rocket", _WEEKDAYS, [
        ("Hacer la cama", "fluent/bed"),
        ("Vestirse", "fluent/t-shirt"),
        ("Desayunar", "fluent/bowl-with-spoon"),
        ("Lavarse los dientes", "fluent/toothbrush"),
        ("Peinarse", None),
        ("Preparar la mochila", "fluent/backpack"),
    ]),
    _sample_template("aterrizaje", "Aterrizaje", "fluent/airplane-arrival", _WEEKDAYS, [
        ("Quitarse los zapatos", "fluent/running-shoe"),
        ("Lavarse las manos", "fluent/soap"),
        ("Merendar", "fluent/green-apple"),
        ("Hacer los deberes", "fluent/books"),
    ]),
    _sample_template("alunizaje", "Alunizaje", "fluent/crescent-moon", _ALL_DAYS, [
        ("Ducharse", "fluent/shower"),
        ("Ponerse el pijama", None),
        ("Lavarse los dientes", "fluent/toothbrush"),
        ("Leer un cuento", "fluent/open-book"),
        ("A la cama", "fluent/bed"),
    ]),
]


def _v3_to_v4(doc: dict) -> dict:
    """Add the templates list, with three samples to start from."""
    templates = doc.get("templates")
    return {**doc, "version": 4, "templates": templates if templates is not None else copy.deepcopy(_SAMPLE_TEMPLATES)}


_MIGRATIONS = {
    1: _v1_to_v2,
    2: _v2_to_v3,
    3: _v3_to_v4,
}


def upgrade(doc: dict) -> dict:
    """Return the document at CURRENT_VERSION. The input is not modified."""
    doc = copy.deepcopy(doc)
    version = doc.get("version", 1)
    if version > CURRENT_VERSION:
        raise ConfigVersionError(
            f"config.yaml is version {version}; this app understands up to {CURRENT_VERSION}"
        )
    if version == 1:
        doc = {**copy.deepcopy(_V1_BASE), **doc, "version": 1}
    while version < CURRENT_VERSION:
        doc = _MIGRATIONS[version](doc)
        version += 1
    return doc


def initial() -> dict:
    """The document used when there is no config.yaml yet."""
    return upgrade(_V1_BASE)
