"""Versioned upgrades of config.yaml.

Each migration takes the document at version N and returns it at N + 1.
Migrations are frozen: they hardcode the values of their time and never
import live defaults, so they keep producing the same result forever.
"""

import copy

CURRENT_VERSION = 13


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


# Daily prizes (paso-5.html), with fixed ids like the sample templates.
_SAMPLE_PRIZES = [
    {"id": "guerra-de-cojines", "text": "Guerra de cojines", "image": None, "image_suggested": False},
    {"id": "elegir-la-cena", "text": "Elegir la cena", "image": "fluent/pizza", "image_suggested": False},
    {"id": "un-cuento-mas", "text": "Un cuento más", "image": "fluent/open-book", "image_suggested": False},
    {"id": "mas-juego", "text": "15 minutos más de juego", "image": "fluent/joystick", "image_suggested": False},
]


def _v5_to_v6(doc: dict) -> dict:
    """Add the list of daily prizes, with four samples to edit or delete."""
    return {**doc, "version": 6, "prizes": copy.deepcopy(_SAMPLE_PRIZES)}


# The morning routine as it was in the old app (an earlier version,
# data/alarms/alarms.yaml, tested at home), for every child. "warnings": the
# minutes before a part ends when the voice warns; None takes the default
# (settings.routine_warn_minutes). The breakfast had a 5-minute warning too.
def _part(name, image, minutes, *, at=None, say=None, tasks=(), warnings=None, check_mission=False):
    return {
        "name": name, "image": image, "at": at, "minutes": minutes, "say": say,
        "tasks": list(tasks), "warnings": warnings, "check_mission": check_mission,
    }


_SAMPLE_ROUTINES = [
    {
        "id": "manana",
        "name": "Mañana",
        "days": ["mon", "tue", "wed", "thu", "fri"],
        "kids": [],  # empty: every child
        "wake": "06:30",
        "remind_every": 5,
        "mission": "Despegue",  # each child's mission with this name
        "parts": [
            _part("la preparación del desayuno", "fluent/cooking", 10, at="06:35", say="Es hora de hacer el desayuno."),
            _part("el desayuno", "fluent/bowl-with-spoon", 15, at="06:45", warnings=[5, 1]),
            _part("el aseo", "fluent/toothbrush", 5, tasks=["Lavarse los dientes", "Lavarse la cara"]),
            _part("vestirse", "fluent/t-shirt", 7, say="Es hora de vestirse y hacer la cama."),
            _part("peinarse y acicalarse", "fluent/woman-getting-haircut", 7,
                  say="Es hora de peinarse y acicalarse.", tasks=["Peinarse", "Echarse colonia", "Ponerse el reloj"]),
            _part("prepararse para salir", "fluent/coat", 6, say="Es hora de prepararse para salir.",
                  tasks=["Abrigo, chal y gorro", "Calzado", "Mochila"]),
            _part("firmar las tareas", "fluent/writing-hand", 5, at="07:30",
                  say="No olvidéis firmar vuestras tareas antes de iros.", check_mission=True),
        ],
        "goal": {"name": "vuestra clase", "image": "fluent/school", "at": "07:45", "say": "¡Es hora de irse al cole!"},
    },
]


def _v6_to_v7(doc: dict) -> dict:
    """Add the routines, starting with the morning one of the old app."""
    return {**doc, "version": 7, "routines": copy.deepcopy(_SAMPLE_ROUTINES)}


def _v7_to_v8(doc: dict) -> dict:
    """Routines get their children and each child's mission by id (the mission
    with the routine's mission name, if they have one), and their parts an id."""
    children = [c["id"] for c in doc.get("children") or []]
    routines = []
    for routine in copy.deepcopy(doc.get("routines") or []):
        kids = routine.get("kids") or []  # empty: every child, also the ones added later
        name = routine.pop("mission", None)
        missions = {}
        for kid in kids or children:
            found = next((m["id"] for m in doc.get("missions") or []
                          if m.get("child_id") == kid and m.get("name") == name), None)
            missions[kid] = found
        for index, part in enumerate(routine.get("parts") or []):
            part.setdefault("id", f"{routine['id']}-{index + 1}")
        routines.append({**routine, "kids": list(kids), "missions": missions})
    return {**doc, "version": 8, "routines": routines}


# The shop (step 6): what the stars buy, the same for every child.
_SAMPLE_SHOP = [
    {"id": "elegir-postre", "text": "Elegir el postre", "image": "fluent/ice-cream", "image_suggested": False,
     "price": 3},
    {"id": "globo", "text": "Un globo", "image": "fluent/balloon", "image_suggested": False, "price": 5},
    {"id": "peluche", "text": "Un peluche", "image": "fluent/teddy-bear", "image_suggested": False, "price": 20},
]


def _v8_to_v9(doc: dict) -> dict:
    """Add the shop, with three samples to edit or delete."""
    return {**doc, "version": 9, "shop": copy.deepcopy(_SAMPLE_SHOP)}


def _v9_to_v10(doc: dict) -> dict:
    """The goal loses its name (the voice says "para terminar"), and the sentences
    the code used to say become the routine's own, so they sound the same as before."""
    routines = []
    for routine in copy.deepcopy(doc.get("routines") or []):
        goal = routine.get("goal")
        if goal:
            goal.pop("name", None)
        if routine.get("wake") is not None:
            routine.setdefault("greeting", "¡Buenos días!")
        routine.setdefault("last_countdown", "Diez segundos para salir." if goal else "Diez segundos.")
        if goal:
            routine.setdefault("early_goal", "¡Ya podéis salir de casa! ¡Que tengáis un buen día!")
        routines.append(routine)
    return {**doc, "version": 10, "routines": routines}


def _v10_to_v11(doc: dict) -> dict:
    """The family's songs (rutinas-4): a library, and the songs each routine plays."""
    routines = [{**routine, "music": routine.get("music") or []} for routine in copy.deepcopy(doc.get("routines") or [])]
    return {**doc, "version": 11, "songs": doc.get("songs") or [], "routines": routines}


def _v11_to_v12(doc: dict) -> dict:
    """Checking the missions is part of the goal (rutinas-6): a last part that checked
    them ("firmar las tareas") becomes the goal's checking, with its minutes and its
    sentence, so the times stay the same. No part checks missions any more."""
    routines = []
    for routine in copy.deepcopy(doc.get("routines") or []):
        parts = routine.get("parts") or []
        goal = routine.get("goal")
        last = parts[-1] if parts else None
        if goal and routine.get("wake") is not None and len(parts) > 1 and last.get("check_mission"):
            parts.pop()
            goal["check_minutes"] = last.get("minutes", 0)
            goal["check_say"] = last.get("say")
            for music in routine.get("music") or []:  # songs at that part go to the goal
                if music.get("start") == last.get("id"):
                    music["start"] = "goal"
                if music.get("until") == last.get("id"):
                    music["until"] = "goal"
        for part in parts:
            part.pop("check_mission", None)
        routines.append({**routine, "parts": parts})
    return {**doc, "version": 12, "routines": routines}


def _v12_to_v13(doc: dict) -> dict:
    """A routine's song becomes a list of songs, one after the other (04/11)."""
    routines = []
    for routine in copy.deepcopy(doc.get("routines") or []):
        for music in routine.get("music") or []:
            if "songs" not in music:
                music["songs"] = [music.pop("song")] if music.get("song") else []
        routine["music"] = [m for m in routine.get("music") or [] if m["songs"]]
        routines.append(routine)
    return {**doc, "version": 13, "routines": routines}


_MIGRATIONS = {
    1: _v1_to_v2,
    2: _v2_to_v3,
    3: _v3_to_v4,
    4: _v4_to_v5,
    5: _v5_to_v6,
    6: _v6_to_v7,
    7: _v7_to_v8,
    8: _v8_to_v9,
    9: _v9_to_v10,
    10: _v10_to_v11,
    11: _v11_to_v12,
    12: _v12_to_v13,
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
