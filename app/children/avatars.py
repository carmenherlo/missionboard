"""Built-in avatars and the fixed colour palette.

Every preset owns one palette colour and can only be used by one child.
Children with a photo pick any palette colour, even one already in use.
Each preset's picture is an image reference from the image libraries.
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
    {"id": "unicorn", "label": "Unicornio", "image": "fluent/unicorn", "color": "#9d4edd"},
    {"id": "dinosaur", "label": "Dinosaurio", "image": "fluent/t-rex", "color": "#52b788"},
    {"id": "dolphin", "label": "Delfín", "image": "fluent/dolphin", "color": "#4895ef"},
    {"id": "fox", "label": "Zorro", "image": "fluent/fox", "color": "#f8961e"},
    {"id": "lion", "label": "León", "image": "fluent/lion", "color": "#f9c74f"},
    {"id": "octopus", "label": "Pulpo", "image": "fluent/octopus", "color": "#f72585"},
    {"id": "ladybug", "label": "Mariquita", "image": "fluent/lady-beetle", "color": "#e63946"},
    {"id": "owl", "label": "Búho", "image": "fluent/owl", "color": "#8d6e63"},
]

PALETTE_COLORS = {entry["color"] for entry in PALETTE}
PRESETS_BY_ID = {preset["id"]: preset for preset in PRESETS}
