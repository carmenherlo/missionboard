"""The mission templates the app brings (primer-arranque.html): a new installation has no
missions, and a family starts from these or from scratch. They live here, in the code, not in
config.yaml; using one copies it (see service.py), and the copy is the family's.

Without a schedule (always open): times are each family's to set. The days and the days of
some tasks are a starting point, there to see and change in the mission."""

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]
NOT_SATURDAY = [*WEEKDAYS, "sun"]
NOT_SATURDAY_NOR_FRIDAY = ["mon", "tue", "wed", "thu", "sun"]  # the night before a day without school


def _step(task_id: str, n: int, text: str, image: str) -> dict:
    return {"id": f"{task_id}-{n}", "text": text, "image": f"fluent/{image}", "image_suggested": False}


def _tasks(mission_id: str, tasks: list[tuple]) -> list[dict]:
    """(text, image[, steps as (text, image)[, days]])"""
    found = []
    for n, (text, image, *rest) in enumerate(tasks, start=1):
        task_id = f"{mission_id}-{n}"
        steps = rest[0] if rest else []
        found.append(
            {
                "id": task_id,
                "text": text,
                "image": image if "/" in image else f"fluent/{image}",
                "image_suggested": False,
                "days": rest[1] if len(rest) > 1 else None,
                "steps": [_step(task_id, i, *step) for i, step in enumerate(steps, start=1)],
            }
        )
    return found


def _mission(mission_id: str, name: str, image: str, color: str, days: list[str], tasks: list[tuple]) -> dict:
    return {
        "id": mission_id,
        "name": name,
        "image": f"fluent/{image}",
        "image_suggested": False,
        "color": color,
        "days": days,
        "schedule": None,  # always open: each family sets its own times
        "tasks": _tasks(mission_id, tasks),
        "kids": [],  # a copy is for every child (service.py)
        "off": {},
    }


TEMPLATES = [
    _mission(
        "despegue",
        "Despegue",
        "rocket",
        "#2193d6",
        WEEKDAYS,
        [
            ("Despertarse", "sleeping-face"),
            ("Desayunar", "bowl-with-spoon"),
            ("Recoger el desayuno", "fork-and-knife-with-plate"),
            ("Aseo", "soap", [("Dientes", "toothbrush"), ("Cara", "droplet")]),
            ("Vestirse", "womans-clothes", [("Ropa", "t-shirt"), ("Reloj", "watch")]),
            ("Acicalarse", "woman-getting-haircut", [("Peinarse", "hair-pick"), ("Colonia", "lotion-bottle")]),
            (
                "Prepararse para salir",
                "door",
                [
                    ("Gorro", "billed-cap"),
                    ("Bufanda", "scarf"),
                    ("Abrigo", "coat"),
                    ("Guantes", "gloves"),
                    ("Mochila", "backpack"),
                ],
            ),
        ],
    ),
    _mission(
        "aterrizaje",
        "Aterrizaje",
        "airplane-arrival",
        "#e77300",
        WEEKDAYS,
        [
            (
                "Guardar abrigo y mochila",
                "basket",
                [
                    ("Abrigo", "coat"),
                    ("Bufanda", "scarf"),
                    ("Gorro", "billed-cap"),
                    ("Guantes", "gloves"),
                    ("Mochila", "backpack"),
                ],
            ),
            ("Quitarse los zapatos", "running-shoe"),
            ("Lavarse las manos", "hand-with-fingers-splayed"),
            ("Ponerse el pijama", "own/pajamas"),
            ("Guardar la ropa", "basket"),
        ],
    ),
    _mission(
        "alunizaje",
        "Alunizaje",
        "crescent-moon",
        "#9471e7",
        NOT_SATURDAY,
        [
            ("Recoger la cena", "fork-and-knife-with-plate"),
            ("Recoger la habitación", "teddy-bear"),
            ("Preparar la ropa de mañana", "t-shirt", [], NOT_SATURDAY_NOR_FRIDAY),
            ("Preparar la mochila", "backpack", [], NOT_SATURDAY_NOR_FRIDAY),
            ("Lavarse los dientes", "toothbrush"),
        ],
    ),
]


def get(template_id: str) -> dict | None:
    return next((t for t in TEMPLATES if t["id"] == template_id), None)
