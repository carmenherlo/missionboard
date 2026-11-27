"""The examples: three children with three missions, their routines and songs. Not for
a family's installation (that one starts empty, primer-arranque.html): for development,
screenshots and trying things out (`create_app(first_run=SAMPLES)`). Fixed ids, so what
they refer to is easy to follow in config.yaml; the children's are drawn each time, like a
child added by hand."""

import secrets
from pathlib import Path

from app.mission_templates import catalog
from app.mission_templates.catalog import NOT_SATURDAY, WEEKDAYS
from app.storage.config_migrations import initial

STARTING_STARS = 5

# Example songs, in the repository: on a new installation they are copied to the
# family's song library (data/sounds/), where they can be changed or deleted like any other.
SOUNDS_DIR = Path(__file__).parent / "samples_sounds"
SONGS = [
    {
        "id": "buenos-dias-solecito",
        "name": "Buenos días, solecito",
        "file": "buenos-dias-solecito.m4a",
        "seconds": 131.2,
    },
    {"id": "duerme-estrellita", "name": "Duerme, Estrellita", "file": "duerme-estrellita.m4a", "seconds": 182.0},
]

CHILDREN = [
    {"id": "bea", "name": "Bea", "preset": "fox", "color": "#e77300"},
    {"id": "alex", "name": "Alex", "preset": "dinosaur", "color": "#4da33d"},
    {"id": "noa", "name": "Noa", "preset": "unicorn", "color": "#9471e7"},
]


# The examples' missions: the app's templates, with the times the examples' routines expect.
SCHEDULES = {"despegue": ("06:00", "09:00"), "aterrizaje": ("12:00", "18:00"), "alunizaje": ("18:00", "20:00")}
MISSIONS = [
    {**template, "schedule": {"start": SCHEDULES[template["id"]][0], "end": SCHEDULES[template["id"]][1]}}
    for template in catalog.TEMPLATES
]


def _part(part_id: str, minutes: int, spoken: str | None = None, say: str | None = None, at: str | None = None) -> dict:
    return {"id": part_id, "at": at, "minutes": minutes, "spoken": spoken, "say": say, "warnings": None}


# From their first part to their goal, with 5 minutes to check the missions before it.
ROUTINES = [
    {
        "id": "despegue-rutina",
        "mission_id": "despegue",
        "days": WEEKDAYS,
        "kids": ["bea", "alex"],
        "wake": "06:35",
        "anchor": "end",
        "alarm": True,
        "remind_every": 5,
        "offsets": {},
        "notices": [],
        "music": [
            {
                "id": "despegue-cancion",
                "songs": ["buenos-dias-solecito"],
                "start": "despegue-1",
                "until": None,
                "after_voice": False,
                "volume": "mid",
            }
        ],
        "last_countdown": None,
        "early_goal": None,
        "warn_about": "end",
        "goal": {"at": "07:35", "image": None, "check_minutes": 5, "check_say": None},
        "parts": [
            _part("despegue-1", 10, say="Ahora toca despertarse.", at="06:40"),
            _part("despegue-2", 15, say="Ahora toca desayunar."),
            _part("despegue-3", 3, say="Ahora toca recoger el desayuno."),
            _part("despegue-4", 7, spoken="el aseo"),
            _part("despegue-5", 5, say="Ahora toca vestirse: ropa y reloj."),
            _part("despegue-6", 5, say="Ahora toca acicalarse: peinarse y colonia."),
            _part("despegue-7", 5, say="Ahora toca prepararse para salir: gorro, bufanda, abrigo, guantes y mochila."),
        ],
    },
    {
        "id": "alunizaje-rutina",
        "mission_id": "alunizaje",
        "days": NOT_SATURDAY,
        "kids": [],
        "wake": "18:50",
        "anchor": "end",
        "alarm": True,
        "remind_every": 5,
        "offsets": {},
        "notices": [],
        "music": [
            {
                "id": "alunizaje-cancion",
                "songs": ["duerme-estrellita"],
                "start": "goal",
                "until": None,
                "after_voice": True,
                "volume": "mid",
            }
        ],
        "last_countdown": None,
        "early_goal": None,
        "warn_about": "end",
        "goal": {
            "at": "19:35",
            "image": None,
            "check_minutes": 5,
            "check_say": None,
        },
        "parts": [
            _part("alunizaje-1", 5, say="Ahora toca recoger la cena.", at="19:00"),
            _part("alunizaje-2", 10, say="Ahora toca recoger la habitación."),
            _part("alunizaje-3", 5, say="Ahora toca preparar la ropa de mañana."),
            _part("alunizaje-4", 5, say="Ahora toca preparar la mochila."),
            _part("alunizaje-5", 5, say="Ahora toca lavarse los dientes."),
        ],
    },
]


def document() -> dict:
    """The whole config.yaml of a new installation."""
    ids = {child["id"]: secrets.token_hex(4) for child in CHILDREN}
    return {
        **initial(),
        "settings": {"starting_stars": STARTING_STARS},
        "children": [{**child, "id": ids[child["id"]]} for child in CHILDREN],
        "missions": [{**mission, "kids": list(ids.values())} for mission in MISSIONS],
        "routines": [{**routine, "kids": [ids[kid] for kid in routine["kids"] or ids]} for routine in ROUTINES],
        "songs": [dict(song) for song in SONGS],
    }
