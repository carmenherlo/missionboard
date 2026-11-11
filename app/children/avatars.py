"""Built-in avatars and the fixed colour palette.

Every preset owns one palette colour and can only be used by one child: the
colour of their ring comes from their animal.
Each preset's picture is an image reference from the image libraries.
"""

import math
import re

# Colours a child can name ("soy el naranja"), in suggestion order: each one
# the most distinct (OKLab) from the ones before it; a new child is offered
# the first one no sibling has. The last three are extras: each looks like
# a basic one (rojo/naranja, azul oscuro/azul, turquesa/verde).
# color: the vivid colour (rings, ✓); strong: tone 40 (text on light);
# soft: tone 90 (fills); on: what goes on top of the vivid colour.
# Chosen in paso-3.5.html (23/10/2026).
PALETTE = [
    {"id": "yellow", "label": "Amarillo", "color": "#f6d700", "strong": "#6c5e10", "soft": "#f6e388", "on": "#1a1b21"},
    {"id": "lilac", "label": "Lila", "color": "#9471e7", "strong": "#66558e", "soft": "#e9ddff", "on": "#ffffff"},
    {"id": "green", "label": "Verde", "color": "#4da33d", "strong": "#406836", "soft": "#c1efaf", "on": "#ffffff"},
    {"id": "orange", "label": "Naranja", "color": "#e77300", "strong": "#8b4f24", "soft": "#ffdcc7", "on": "#ffffff"},
    {"id": "pink", "label": "Rosa", "color": "#e865a3", "strong": "#8a4a66", "soft": "#ffd9e5", "on": "#ffffff"},
    {"id": "blue", "label": "Azul", "color": "#2193d6", "strong": "#2a638b", "soft": "#cce5ff", "on": "#ffffff"},
    {"id": "red", "label": "Rojo", "color": "#d3372f", "strong": "#904a43", "soft": "#ffdad5", "on": "#ffffff"},
    {"id": "dark-blue", "label": "Azul oscuro", "color": "#244d99", "strong": "#244d99", "soft": "#d9e2ff", "on": "#ffffff"},
    {"id": "turquoise", "label": "Turquesa", "color": "#00978c", "strong": "#006a62", "soft": "#9df2e7", "on": "#ffffff"},
    # Only for the rings of the animals of these colours (06/11).
    {"id": "peach", "label": "Melocotón", "color": "#f2a36c", "strong": "#8a5a3c", "soft": "#ffe0cc", "on": "#1a1b21"},
    {"id": "brown", "label": "Marrón", "color": "#8d5a3b", "strong": "#6b4226", "soft": "#f0dccb", "on": "#ffffff"},
]

_COLOR = {entry["id"]: entry["color"] for entry in PALETTE}

# Each animal with its natural colour: two or three per colour, so there is
# plenty to choose from (to be replaced by the family's own drawings). In the
# picker's rainbow order. An animal is only for one child; a colour may repeat.
_ANIMALS = [
    ("orange", [("fox", "Zorro", "fox"), ("tiger", "Tigre", "tiger-face")]),
    ("peach", [("hamster", "Hámster", "hamster")]),
    ("red", [("ladybug", "Mariquita", "lady-beetle"), ("butterfly", "Mariposa", "butterfly")]),
    ("yellow", [("lion", "León", "lion"), ("chick", "Pollito", "baby-chick"), ("bee", "Abeja", "honeybee")]),
    ("green", [("dinosaur", "Dinosaurio", "t-rex"), ("frog", "Rana", "frog"), ("turtle", "Tortuga", "turtle")]),
    ("turquoise", [("fish", "Pez tropical", "tropical-fish")]),
    ("blue", [("dolphin", "Delfín", "dolphin"), ("whale", "Ballena", "spouting-whale")]),
    ("dark-blue", [("penguin", "Pingüino", "penguin")]),
    ("brown", [("owl", "Búho", "owl")]),
    ("lilac", [("unicorn", "Unicornio", "unicorn"), ("jellyfish", "Medusa", "jellyfish")]),
    ("pink", [("crab", "Cangrejo", "crab"), ("octopus", "Pulpo", "octopus"), ("pig", "Cerdito", "pig-face"), ("flamingo", "Flamenco", "flamingo")]),
]

PRESETS = [
    {"id": preset_id, "label": label, "image": f"fluent/{image}", "color": _COLOR[colour]}
    for colour, animals in _ANIMALS
    for preset_id, label, image in animals
]

PALETTE_COLORS = {entry["color"] for entry in PALETTE}
# What a mission can be: every colour but the two that are only for rings.
MISSION_COLORS = [entry["color"] for entry in PALETTE if entry["id"] not in ("peach", "brown")]
_BY_COLOR = {entry["color"]: entry for entry in PALETTE}


def tones(color: str) -> dict:
    """The child's colour with its tones (fills, text, what goes on top).

    The palette's are chosen by hand; any other colour (a family avatar's, avatares.html)
    has them worked out: the same hue, light for fills and dark for text.
    """
    entry = _BY_COLOR.get(color)
    if entry is None:
        return derived_tones(color)
    return {key: entry[key] for key in ("color", "strong", "soft", "on")}


# ---------- tones of any colour (OKLCH: lightness, chroma, hue) ----------

HEX_COLOR = re.compile(r"^#[0-9a-f]{6}$")
_SOFT = (0.92, 0.06)  # lightness and most chroma of the fills, like the palette's tone 90
_STRONG = (0.45, 0.12)  # of the text on light, like tone 40
_DARK_ON = "#1a1b21"  # what goes on light colours (the palette's yellow and peach)


def derived_tones(color: str) -> dict:
    _, chroma, hue = _oklch(color)
    return {
        "color": color,
        "strong": _from_oklch(_STRONG[0], min(chroma, _STRONG[1]), hue),
        "soft": _from_oklch(_SOFT[0], min(chroma, _SOFT[1]), hue),
        # As the palette: a white ✓ wherever it reads (3:1, the size of an icon), else dark.
        "on": "#ffffff" if _contrast(color, "#ffffff") >= 3 else _DARK_ON,
    }


def _linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gamma(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def _rgb(color: str) -> tuple[float, float, float]:
    return tuple(_linear(int(color[i:i + 2], 16) / 255) for i in (1, 3, 5))


def _oklch(color: str) -> tuple[float, float, float]:
    r, g, b = _rgb(color)
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    lightness = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return lightness, math.hypot(a, bb), math.atan2(bb, a)


def _from_oklch(lightness: float, chroma: float, hue: float) -> str:
    """The colour, with less chroma until it can be shown (sRGB)."""
    while True:
        a, b = chroma * math.cos(hue), chroma * math.sin(hue)
        l_ = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
        m_ = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
        s_ = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
        rgb = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
               -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
               -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
        if all(-1e-4 <= c <= 1 + 1e-4 for c in rgb) or chroma < 0.001:
            return "#" + "".join(f"{round(min(1, max(0, _gamma(min(1, max(0, c))))) * 255):02x}" for c in rgb)
        chroma -= 0.005


def _luminance(color: str) -> float:
    r, g, b = _rgb(color)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(one: str, other: str) -> float:
    lighter, darker = sorted((_luminance(one), _luminance(other)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


PRESETS_BY_ID = {preset["id"]: preset for preset in PRESETS}
