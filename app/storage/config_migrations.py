"""Versioned upgrades of config.yaml.

Each migration takes the document at version N and returns it at N + 1, and is
frozen: it hardcodes the values of its time. They start at FIRST_VERSION: files
older than that are not converted (see fresh_start.py).
"""

import copy
from collections.abc import Callable

from app.storage.config_initial import PRIZES, SHOP

FIRST_VERSION = 16  # family missions: mission → task → step
CURRENT_VERSION = 28


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
        seasons.append(
            {
                "name": season["name"],
                "start": season["start"],
                "manana": _hhmm(sunrise - margin),
                "dia": _hhmm(sunrise + margin),
                "tarde": _hhmm(sunset - margin),
                "noche": _hhmm(sunset + margin),
            }
        )
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


def _v19_to_v20(doc: dict) -> dict:
    """The phones, chosen once for everything that sends a message (padres-menu.html):
    from the shop's settings to their own; the shop keeps a switch, on."""
    settings = doc.setdefault("settings", {})
    shop = settings.get("shop_notify")
    if isinstance(shop, dict):
        phones = shop.pop("phones", [])
        shop["on"] = True
        settings["notify"] = {"phones": list(phones or [])}
    doc["version"] = 20
    return doc


_MIGRATIONS[19] = _v19_to_v20


def _v20_to_v21(doc: dict) -> dict:
    """The week's smaller prize (20/11): from "at least N days" to a share of the days that
    count, so that days let off do not change what it asks: N of the week's days, to the
    nearest 10 % (3 of 5: 60 %)."""
    week = doc.get("settings", {}).get("streak_week")
    if isinstance(week, dict) and "second_min" in week:
        days = len(week.get("days") or ["mon", "tue", "wed", "thu", "fri"])
        share = round(week.pop("second_min") / days * 10) * 10
        week["second_percent"] = min(90, max(10, share))
    doc["version"] = 21
    return doc


_MIGRATIONS[20] = _v20_to_v21


def _v21_to_v22(doc: dict) -> dict:
    """Rachas (20/11): a day fills its tank only with all its missions done.
    The choice "at least one" goes."""
    doc.get("settings", {}).pop("streak_rule", None)
    doc["version"] = 22
    return doc


_MIGRATIONS[21] = _v21_to_v22


def _v22_to_v23(doc: dict) -> dict:
    """Rutinas (rutina-modos.html, 24/11): every routine has its goal, and what the alarm
    and the goal say is fixed ("Va a empezar la misión…", "¡Misión … completada!"): their
    own sentences go. A routine without a goal gets one with no checking, when its parts end."""
    for routine in doc.get("routines") or []:
        routine.pop("greeting", None)
        goal = routine.get("goal")
        if goal:
            goal.pop("say", None)
            continue
        parts = routine.get("parts") or []
        first = parts and (parts[0].get("at") or routine.get("wake"))
        at = None
        if routine.get("wake") is not None and first:
            at = _hhmm(_minutes(first) + sum(part.get("minutes", 0) for part in parts))
        routine["goal"] = {"at": at, "image": None, "check_minutes": 0, "check_say": None}
    doc["version"] = 23
    return doc


_MIGRATIONS[22] = _v22_to_v23


def _v23_to_v24(doc: dict) -> dict:
    """El Inicio (rutina-inicio.html, 24/11): "Va a empezar la misión…" and 5, 4, 3, 2, 1
    always come before the first part, so a routine with no warning before (no alarm, or
    ringing as it starts) opens a minute before, quietly; and a warning repeats every 5
    minutes or not at all."""
    for routine in doc.get("routines") or []:
        parts = routine.get("parts") or []
        if routine.get("wake") is None or not parts:
            continue
        first = parts[0].get("at") or routine["wake"]
        if not routine.get("alarm", True) or _minutes(first) == _minutes(routine["wake"]):
            routine["alarm"] = False
            routine["wake"] = _hhmm(_minutes(first) - 1)
            parts[0]["at"] = first
        if routine.get("remind_every", 5):
            routine["remind_every"] = 5
    doc["version"] = 24
    return doc


_MIGRATIONS[23] = _v23_to_v24


def _v24_to_v25(doc: dict) -> dict:
    """Each song of a routine, low, mid or high (24/11), instead of "muy alta" or not."""
    for routine in doc.get("routines") or []:
        for music in routine.get("music") or []:
            music["volume"] = "high" if music.pop("loud", False) else "mid"
    doc["version"] = 25
    return doc


_MIGRATIONS[24] = _v24_to_v25


def _v25_to_v26(doc: dict) -> dict:
    """The warning before each task ends (24/11): always a minute, unless the task has its
    own; the setting for every routine goes."""
    (doc.get("settings") or {}).pop("routine_warn_minutes", None)
    doc["version"] = 26
    return doc


_MIGRATIONS[25] = _v25_to_v26


def _v26_to_v27(doc: dict) -> dict:
    """The alien trains (carrera-estrategia.html, 24/11): "muy rápido" and its stars go
    (the record gives one more instead)."""
    for routine in doc.get("routines") or []:
        if isinstance(routine.get("race"), dict):
            routine["race"].pop("fast", None)
    doc["version"] = 27
    return doc


_MIGRATIONS[26] = _v26_to_v27


def _v27_to_v28(doc: dict) -> dict:
    """The day always starts at 00:00 (misiones-para-quien.html, 27/11): its setting goes."""
    (doc.get("settings") or {}).pop("day_starts_at", None)
    doc["version"] = 28
    return doc


_MIGRATIONS[27] = _v27_to_v28


def upgrade(doc: dict) -> dict:
    """Return the document at CURRENT_VERSION. The input is not modified."""
    version = doc.get("version", 1)
    if version > CURRENT_VERSION:
        raise ConfigVersionError(f"config.yaml is version {version}; this app understands up to {CURRENT_VERSION}")
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
        "settings": {"stars_per_mission": 1, "daily_prize_spins": 1},
        "features": {
            "daily_prize": True,
            "shop": True,
            "streaks": True,
            "dashboard": True,
            "routines": True,
            "games": False,
        },
        "missions": [],
        "routines": [],
        "songs": [],
        "avatars": [],
        "prizes": copy.deepcopy(PRIZES),
        "shop": copy.deepcopy(SHOP),
    }
