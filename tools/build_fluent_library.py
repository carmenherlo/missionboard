"""Build the Fluent Emoji image library from its sources.

Run once (or to update), then commit the result:

    python tools/build_fluent_library.py FLUENT_REPO CLDR_DIR

FLUENT_REPO: a checkout of https://github.com/microsoft/fluentui-emoji
    (only assets/*/metadata.json and the Color SVGs are needed).
CLDR_DIR: a folder with the Spanish emoji annotations from
    https://github.com/unicode-org/cldr-json, saved as
    cldr-annotations-full.json and cldr-annotations-derived-full.json.

Writes app/static/libraries/fluent/: one SVG per emoji, catalog.json
(Spanish names and keywords for the search) and the licenses.
"""

import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "app" / "static" / "libraries" / "fluent"

GROUPS_ES = {
    "Smileys & Emotion": "Caras y emociones",
    "People & Body": "Personas y cuerpo",
    "Animals & Nature": "Animales y naturaleza",
    "Food & Drink": "Comida y bebida",
    "Travel & Places": "Viajes y lugares",
    "Activities": "Actividades",
    "Objects": "Objetos",
    "Symbols": "Símbolos",
    "Flags": "Banderas",
}

# What the picker shows before searching: images useful for routines, by theme.
# Names are Fluent's English CLDR names.
FEATURED = {
    "Mañana y noche": [
        "sunrise", "sun", "alarm clock", "bed", "sleeping face", "yawning face", "crescent moon",
        "night with stars", "zzz", "teddy bear", "hourglass not done", "mantelpiece clock",
    ],
    "Higiene": [
        "toothbrush", "tooth", "soap", "bubbles", "shower", "bathtub", "person taking bath", "toilet",
        "roll of paper", "sponge", "lotion bottle", "droplet", "nail polish", "person getting haircut",
        "mirror", "nose",
    ],
    "Ropa": [
        "t-shirt", "jeans", "shorts", "dress", "socks", "coat", "scarf", "gloves", "billed cap",
        "running shoe", "hiking boot", "thong sandal", "one-piece swimsuit", "briefs", "glasses",
        "backpack",
    ],
    "Comida": [
        "bowl with spoon", "bread", "croissant", "pancakes", "cooking", "egg", "glass of milk",
        "hot beverage", "cup with straw", "red apple", "banana", "pear", "tangerine", "strawberry",
        "grapes", "watermelon", "carrot", "broccoli", "green salad", "avocado", "cheese wedge",
        "sandwich", "pizza", "spaghetti", "steaming bowl", "cooked rice", "poultry leg", "fish",
        "cookie", "fork and knife", "fork and knife with plate", "spoon", "baby bottle",
    ],
    "Casa y tareas": [
        "house", "door", "window", "broom", "basket", "bucket", "wastebasket", "recycling symbol",
        "chair", "couch and lamp", "potted plant", "light bulb", "key", "toolbox",
        "magic wand",
    ],
    "Cole y aprender": [
        "school", "books", "open book", "notebook", "pencil", "crayon", "paintbrush", "artist palette",
        "scissors", "straight ruler", "abacus", "memo", "calendar", "laptop", "graduation cap",
        "globe showing Europe-Africa",
    ],
    "Salir": [
        "bus", "automobile", "bicycle", "kick scooter", "person walking", "umbrella", "sunglasses",
        "vertical traffic light", "stop sign", "world map", "national park", "playground slide",
    ],
    "Juego y actividades": [
        "soccer ball", "basketball", "tennis", "puzzle piece", "video game", "game die", "kite",
        "balloon", "yo-yo", "chess pawn", "brick", "guitar", "drum", "musical note", "headphone",
        "television", "mobile phone", "person swimming", "person cartwheeling", "trophy",
        "sports medal", "party popper", "wrapped gift",
    ],
    "Emociones": [
        "grinning face", "smiling face with smiling eyes", "star-struck", "partying face",
        "hugging face", "relieved face", "thinking face", "crying face", "angry face",
        "face with thermometer", "red heart", "thumbs up", "clapping hands", "flexed biceps",
        "raising hands", "waving hand", "folded hands", "people hugging",
    ],
    "Animales": [
        "dog", "cat", "rabbit", "hamster", "bird", "fish", "turtle", "horse", "unicorn", "T-Rex",
        "sauropod", "lion", "fox", "octopus", "lady beetle", "owl", "dolphin", "butterfly",
        "honeybee", "chicken", "cow face", "pig face",
    ],
    "Espacio": [
        "rocket", "flying saucer", "full moon", "ringed planet", "star", "glowing star", "sparkles",
        "comet", "milky way", "satellite", "telescope", "airplane departure", "airplane arrival",
    ],
}

# Extra Spanish words families use that CLDR does not include.
EXTRA_KEYWORDS = {
    "backpack": ["mochila", "cole", "colegio"],
    "school": ["cole", "colegio"],
    "bowl with spoon": ["cereales", "desayunar"],
    "toothbrush": ["dientes", "lavarse", "cepillarse"],
    "bed": ["dormir", "hacer la cama", "acostarse"],
    "t-shirt": ["vestirse", "ropa", "camiseta"],
    "jeans": ["vestirse", "ropa", "pantalón"],
    "running shoe": ["zapatos", "zapatillas", "calzarse"],
    "shower": ["ducharse", "ducha"],
    "bathtub": ["bañarse", "baño"],
    "soap": ["lavarse las manos", "manos"],
    "broom": ["barrer", "limpiar", "recoger"],
    "basket": ["recoger", "ropa sucia", "cesto"],
    "wastebasket": ["basura", "tirar"],
    "books": ["deberes", "estudiar", "leer"],
    "open book": ["leer", "lectura", "deberes"],
    "pencil": ["deberes", "escribir", "lápiz"],
    "crescent moon": ["noche", "dormir"],
    "sunrise": ["mañana", "despertarse", "levantarse"],
    "alarm clock": ["despertarse", "levantarse", "hora"],
    "fork and knife with plate": ["comer", "comida", "cenar", "poner la mesa"],
    "fork and knife": ["comer", "poner la mesa", "cubiertos"],
    "glass of milk": ["leche", "desayuno", "merienda"],
    "teddy bear": ["juguetes", "recoger juguetes", "peluche"],
    "rocket": ["despegue", "misión"],
    "airplane arrival": ["aterrizaje", "llegar a casa"],
    "full moon": ["alunizaje", "noche"],
    "toilet": ["váter", "baño", "pis", "caca"],
    "person walking": ["andar", "paseo", "caminar"],
    "glasses": ["gafas"],
    "coat": ["abrigo", "abrigarse"],
    "scarf": ["bufanda", "abrigarse"],
    "gloves": ["guantes", "abrigarse"],
    "billed cap": ["gorra", "gorro"],
}


def slug(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


def color_svg(asset_dir: Path) -> Path | None:
    for pattern in ("Color/*.svg", "Default/Color/*.svg"):
        found = sorted(asset_dir.glob(pattern))
        if found:
            return found[0]
    return None


def load_cldr(cldr_dir: Path) -> dict:
    annotations = {}
    for name, key in (
        ("cldr-annotations-derived-full.json", "annotationsDerived"),
        ("cldr-annotations-full.json", "annotations"),
    ):
        data = json.loads((cldr_dir / name).read_text(encoding="utf-8"))
        annotations.update(data[key]["annotations"])
    return annotations


def spanish(glyph: str, cldr: dict) -> dict | None:
    # Fluent glyphs sometimes carry or lack the emoji variation selector (U+FE0F).
    for candidate in (glyph, glyph.replace("️", ""), glyph + "️"):
        if candidate in cldr:
            return cldr[candidate]
    return None


def build(fluent_repo: Path, cldr_dir: Path) -> None:
    cldr = load_cldr(cldr_dir)
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)

    items, by_name, missing_es = [], {}, []
    for meta_path in sorted((fluent_repo / "assets").glob("*/metadata.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        svg = color_svg(meta_path.parent)
        if svg is None:
            continue
        item_id = slug(meta["cldr"])
        es = spanish(meta["glyph"], cldr)
        if es is None:
            missing_es.append(meta["cldr"])
            name, keywords = meta["cldr"], []
        else:
            name = es["tts"][0]
            keywords = [k for k in es.get("default", []) if k != name]
        extra = [k for k in EXTRA_KEYWORDS.get(meta["cldr"], []) if k not in keywords]
        shutil.copyfile(svg, OUT_DIR / f"{item_id}.svg")
        item = {
            "id": item_id,
            "name": name,
            "keywords": keywords + extra,
            "group": GROUPS_ES.get(meta.get("group"), meta.get("group")),
        }
        items.append(item)
        by_name[meta["cldr"]] = item_id

    featured, unknown = [], []
    for theme, names in FEATURED.items():
        ids = []
        for name in names:
            if name in by_name:
                ids.append(by_name[name])
            else:
                unknown.append(name)
        featured.append({"name": theme, "items": ids})

    catalog = {
        "id": "fluent",
        "name": "Fluent Emoji",
        "license": "MIT © Microsoft Corporation · palabras clave: Unicode CLDR",
        "featured": featured,
        "items": items,
    }
    (OUT_DIR / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    shutil.copyfile(fluent_repo / "LICENSE", OUT_DIR / "LICENSE-fluent-emoji.txt")
    if (cldr_dir / "LICENSE").exists():
        shutil.copyfile(cldr_dir / "LICENSE", OUT_DIR / "LICENSE-unicode-cldr.txt")

    print(f"{len(items)} images, {sum(len(f['items']) for f in featured)} featured")
    if unknown:
        print("Featured names not found:", ", ".join(unknown))
    if missing_es:
        print(f"{len(missing_es)} without Spanish annotations:", ", ".join(missing_es[:20]))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(Path(sys.argv[1]), Path(sys.argv[2]))
