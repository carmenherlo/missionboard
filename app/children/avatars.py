"""Built-in avatars and the fixed colour palette.

Every preset owns one palette colour and can only be used by one child.
Children with a photo pick any palette colour, even one already in use.
Each preset's picture is an image reference from the image libraries.
"""

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
]

# The colour picker: six columns in rainbow order, the basic colours on top
# and each extra under the basic one it looks like, so two colours of the
# same column are easy to spot (better not to give them to two siblings).
PICKER_COLUMNS = [["orange", "red"], ["yellow"], ["green", "turquoise"], ["blue", "dark-blue"], ["lilac"], ["pink"]]

_COLOR = {entry["id"]: entry["color"] for entry in PALETTE}

# Each animal with its natural colour.
PRESETS = [
    {"id": "unicorn", "label": "Unicornio", "image": "fluent/unicorn", "color": _COLOR["lilac"]},
    {"id": "dinosaur", "label": "Dinosaurio", "image": "fluent/t-rex", "color": _COLOR["green"]},
    {"id": "dolphin", "label": "Delfín", "image": "fluent/dolphin", "color": _COLOR["blue"]},
    {"id": "fox", "label": "Zorro", "image": "fluent/fox", "color": _COLOR["orange"]},
    {"id": "lion", "label": "León", "image": "fluent/lion", "color": _COLOR["yellow"]},
    {"id": "octopus", "label": "Pulpo", "image": "fluent/octopus", "color": _COLOR["pink"]},
    {"id": "ladybug", "label": "Mariquita", "image": "fluent/lady-beetle", "color": _COLOR["red"]},
    {"id": "owl", "label": "Búho", "image": "fluent/owl", "color": _COLOR["dark-blue"]},
]

PALETTE_COLORS = {entry["color"] for entry in PALETTE}
_BY_COLOR = {entry["color"]: entry for entry in PALETTE}


def tones(color: str) -> dict:
    """The child's colour with its tones (fills, text, what goes on top).

    A colour outside the palette (written by hand) uses itself for every tone.
    """
    entry = _BY_COLOR.get(color)
    if entry is None:
        return {"color": color, "strong": color, "soft": color, "on": "#ffffff"}
    return {key: entry[key] for key in ("color", "strong", "soft", "on")}
PRESETS_BY_ID = {preset["id"]: preset for preset in PRESETS}
