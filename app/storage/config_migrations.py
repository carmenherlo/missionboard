"""Versioned upgrades of config.yaml.

Each migration takes the document at version N and returns it at N + 1.
Migrations are frozen: they hardcode the values of their time and never
import live defaults, so they keep producing the same result forever.
"""

import copy

CURRENT_VERSION = 5


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


# The children's palette of paso-3.5 (23/10/2026): each animal takes its
# natural colour; a photo child, the new colour closest (OKLab) to its old one.
# Brown was a tie between turquoise and red: red, as brown is warm.
_V5_PRESET_COLORS = {
    "unicorn": "#9471e7",
    "dinosaur": "#4da33d",
    "dolphin": "#2193d6",
    "fox": "#e77300",
    "lion": "#f6d700",
    "octopus": "#e865a3",
    "ladybug": "#d3372f",
    "owl": "#244d99",
}
_V5_OLD_TO_NEW = {
    "#9d4edd": "#9471e7",  # morado → lila
    "#52b788": "#4da33d",  # verde → verde
    "#4895ef": "#2193d6",  # azul → azul
    "#f8961e": "#e77300",  # naranja → naranja
    "#f9c74f": "#f6d700",  # amarillo → amarillo
    "#f72585": "#e865a3",  # rosa → rosa
    "#e63946": "#d3372f",  # rojo → rojo
    "#8d6e63": "#d3372f",  # marrón → rojo
}


def _v4_to_v5(doc: dict) -> dict:
    """Move every child to the new palette of colours a child can name."""
    def recolor(child: dict) -> dict:
        color = child.get("color")
        if child.get("avatar_type") == "preset" and child.get("preset") in _V5_PRESET_COLORS:
            color = _V5_PRESET_COLORS[child["preset"]]
        else:
            color = _V5_OLD_TO_NEW.get(str(color).lower(), color)
        return {**child, "color": color}

    return {**doc, "version": 5, "children": [recolor(c) for c in doc.get("children") or []]}


_MIGRATIONS = {
    1: _v1_to_v2,
    2: _v2_to_v3,
    3: _v3_to_v4,
    4: _v4_to_v5,
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
