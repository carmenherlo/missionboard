"""Built-in avatars and the fixed colour palette.

Every preset owns one palette colour. A child's colour is exclusive, so a preset
is unavailable while another child is using its colour.
"""

PALETTE = [
    {"color": "#9d4edd", "label": "Morado"},
    {"color": "#52b788", "label": "Verde"},
    {"color": "#4895ef", "label": "Azul"},
    {"color": "#f8961e", "label": "Naranja"},
    {"color": "#f9c74f", "label": "Amarillo"},
    {"color": "#f72585", "label": "Rosa"},
    {"color": "#e63946", "label": "Rojo"},
    {"color": "#8d6e63", "label": "Marrón"},
]

PRESETS = [
    {"id": "unicorn", "label": "Unicornio", "emoji": "🦄", "color": "#9d4edd"},
    {"id": "dinosaur", "label": "Dinosaurio", "emoji": "🦖", "color": "#52b788"},
    {"id": "dolphin", "label": "Delfín", "emoji": "🐬", "color": "#4895ef"},
    {"id": "fox", "label": "Zorro", "emoji": "🦊", "color": "#f8961e"},
    {"id": "lion", "label": "León", "emoji": "🦁", "color": "#f9c74f"},
    {"id": "octopus", "label": "Pulpo", "emoji": "🐙", "color": "#f72585"},
    {"id": "ladybug", "label": "Mariquita", "emoji": "🐞", "color": "#e63946"},
    {"id": "owl", "label": "Búho", "emoji": "🦉", "color": "#8d6e63"},
]

PALETTE_COLORS = {entry["color"] for entry in PALETTE}
PRESETS_BY_ID = {preset["id"]: preset for preset in PRESETS}
