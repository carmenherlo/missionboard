"""Versioned upgrades of config.yaml.

Each migration takes the document at version N and returns it at N + 1.
Migrations are frozen: they hardcode the values of their time and never
import live defaults, so they keep producing the same result forever.
"""

import copy

CURRENT_VERSION = 3


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


_MIGRATIONS = {
    1: _v1_to_v2,
    2: _v2_to_v3,
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
