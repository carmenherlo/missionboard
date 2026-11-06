"""What a new installation starts with: three children and three missions, for each
family to change. Fixed ids, so what they refer to is easy to follow in config.yaml."""

from app.storage.config_migrations import initial

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]
NOT_SATURDAY = [*WEEKDAYS, "sun"]
NOT_SATURDAY_NOR_FRIDAY = ["mon", "tue", "wed", "thu", "sun"]  # the night before a day without school
STARTING_STARS = 5

CHILDREN = [
    {"id": "bea", "name": "Bea", "preset": "fox", "color": "#e77300"},
    {"id": "alex", "name": "Alex", "preset": "dinosaur", "color": "#4da33d"},
    {"id": "noa", "name": "Noa", "preset": "unicorn", "color": "#9471e7"},
]


def _step(task_id: str, n: int, text: str, image: str) -> dict:
    return {"id": f"{task_id}-{n}", "text": text, "image": f"fluent/{image}", "image_suggested": False}


def _tasks(mission_id: str, tasks: list[tuple]) -> list[dict]:
    """(text, image[, steps as (text, image)[, days]])"""
    found = []
    for n, (text, image, *rest) in enumerate(tasks, start=1):
        task_id = f"{mission_id}-{n}"
        steps = rest[0] if rest else []
        found.append({
            "id": task_id, "text": text,
            "image": image if "/" in image else f"fluent/{image}", "image_suggested": False,
            "days": rest[1] if len(rest) > 1 else None,
            "steps": [_step(task_id, i, *step) for i, step in enumerate(steps, start=1)],
        })
    return found


def _mission(mission_id: str, name: str, image: str, color: str, days: list[str], start: str, end: str, tasks: list[tuple]) -> dict:
    return {
        "id": mission_id, "name": name, "image": f"fluent/{image}", "image_suggested": False, "color": color,
        "days": days, "schedule": {"start": start, "end": end}, "tasks": _tasks(mission_id, tasks), "off": {},
    }


MISSIONS = [
    _mission("despegue", "Despegue", "rocket", "#2193d6", WEEKDAYS, "07:00", "09:00", [
        ("Despertarse", "sleeping-face"),
        ("Desayunar", "bowl-with-spoon"),
        ("Recoger el desayuno", "fork-and-knife-with-plate"),
        ("Aseo", "soap", [("Dientes", "toothbrush"), ("Cara", "droplet")]),
        ("Vestirse", "womans-clothes", [("Ropa", "t-shirt"), ("Reloj", "watch")]),
        ("Acicalarse", "woman-getting-haircut", [("Peinarse", "hair-pick"), ("Colonia", "lotion-bottle")]),
        ("Prepararse para salir", "door", [("Gorro", "billed-cap"), ("Bufanda", "scarf"), ("Abrigo", "coat"),
                                            ("Guantes", "gloves"), ("Mochila", "backpack")]),
    ]),
    _mission("aterrizaje", "Aterrizaje", "airplane-arrival", "#e77300", WEEKDAYS, "12:00", "18:00", [
        ("Guardar abrigo y mochila", "basket", [("Abrigo", "coat"), ("Bufanda", "scarf"), ("Gorro", "billed-cap"),
                                                 ("Guantes", "gloves"), ("Mochila", "backpack")]),
        ("Quitarse los zapatos", "running-shoe"),
        ("Lavarse las manos", "hand-with-fingers-splayed"),
        ("Ponerse el pijama", "own/pajamas"),
        ("Guardar la ropa", "basket"),
    ]),
    _mission("alunizaje", "Alunizaje", "crescent-moon", "#9471e7", NOT_SATURDAY, "18:00", "20:00", [
        ("Recoger la cena", "fork-and-knife-with-plate"),
        ("Recoger la habitación", "teddy-bear"),
        ("Preparar la ropa de mañana", "t-shirt", [], NOT_SATURDAY_NOR_FRIDAY),
        ("Preparar la mochila", "backpack", [], NOT_SATURDAY_NOR_FRIDAY),
        ("Lavarse los dientes", "toothbrush"),
    ]),
]


def _part(part_id: str, minutes: int, spoken: str | None = None, say: str | None = None, at: str | None = None) -> dict:
    return {"id": part_id, "at": at, "minutes": minutes, "spoken": spoken, "say": say, "warnings": None}


# From their first part to their goal, with 5 minutes to check the missions before it.
ROUTINES = [
    {
        "id": "despegue-rutina", "mission_id": "despegue", "days": WEEKDAYS, "kids": ["bea", "alex"],
        "wake": "06:30", "anchor": "end", "alarm": True, "remind_every": 5, "offsets": {}, "notices": [], "music": [],
        "greeting": "¡Buenos días!", "last_countdown": None, "early_goal": None, "warn_about": "end",
        "goal": {"at": "07:30", "image": None, "say": "¡Es hora de salir!", "check_minutes": 5, "check_say": None},
        "parts": [
            _part("despegue-1", 5, say="Ahora toca despertarse.", at="06:35"),
            _part("despegue-2", 15, say="Ahora toca desayunar."),
            _part("despegue-3", 5, say="Ahora toca recoger el desayuno."),
            _part("despegue-4", 7, spoken="el aseo"),
            _part("despegue-5", 6, say="Ahora toca vestirse: ropa y reloj."),
            _part("despegue-6", 5, say="Ahora toca acicalarse: peinarse y colonia."),
            _part("despegue-7", 7, say="Ahora toca prepararse para salir: gorro, bufanda, abrigo, guantes y mochila."),
        ],
    },
    {
        "id": "alunizaje-rutina", "mission_id": "alunizaje", "days": NOT_SATURDAY, "kids": [],
        "wake": "18:55", "anchor": "end", "alarm": False, "remind_every": 5, "offsets": {}, "notices": [], "music": [],
        "greeting": None, "last_countdown": None, "early_goal": None, "warn_about": "end",
        "goal": {"at": "19:30", "image": None, "say": "¡A dormir! Buenas noches.", "check_minutes": 5, "check_say": None},
        "parts": [
            _part("alunizaje-1", 5, say="Ahora toca recoger la cena.", at="18:55"),
            _part("alunizaje-2", 10, say="Ahora toca recoger la habitación."),
            _part("alunizaje-3", 5, say="Ahora toca preparar la ropa de mañana."),
            _part("alunizaje-4", 5, say="Ahora toca preparar la mochila."),
            _part("alunizaje-5", 5, say="Ahora toca lavarse los dientes."),
        ],
    },
]


def document() -> dict:
    """The whole config.yaml of a new installation."""
    return {
        **initial(),
        "settings": {"starting_stars": STARTING_STARS},
        "children": [dict(child) for child in CHILDREN],
        "missions": MISSIONS,
        "routines": ROUTINES,
    }
