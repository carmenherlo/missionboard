"""What a new install starts with in its prize wheel and its shop (config_migrations.initial)."""

PRIZES = [
    {
        "id": "guerra",
        "text": "Guerra de cojines o de cosquillas",
        "image": "fluent/face-with-tears-of-joy",
        "image_suggested": False,
    },
    {
        "id": "juego",
        "text": "10 minutos de juego con mamá o papá, tú eliges",
        "image": "fluent/game-die",
        "image_suggested": False,
    },
    {
        "id": "bailar",
        "text": "Elige una canción y bailamos todos",
        "image": "fluent/woman-dancing",
        "image_suggested": False,
    },
    {
        "id": "cuento",
        "text": "Eliges el cuento de esta noche",
        "image": "fluent/open-book",
        "image_suggested": False,
    },
    {
        "id": "dinosaurio",
        "text": "Paseo en dinosaurio por toda la casa",
        "image": "fluent/sauropod",
        "image_suggested": False,
    },
    {
        "id": "sitio-en-la-mesa",
        "text": "Eliges tu sitio en la mesa para cenar",
        "image": "fluent/chair",
        "image_suggested": False,
    },
    {"id": "petisui", "text": "Un petisuí extra", "image": "fluent/custard", "image_suggested": False},
]

SHOP = [
    {
        "id": "pegatinas",
        "text": "Unas pegatinas",
        "image": "fluent/sparkles",
        "image_suggested": False,
        "price": 3,
    },
    {"id": "globo", "text": "Un globo", "image": "fluent/balloon", "image_suggested": False, "price": 5},
    {
        "id": "peluche",
        "text": "Un peluche",
        "image": "fluent/teddy-bear",
        "image_suggested": False,
        "price": 20,
    },
]
