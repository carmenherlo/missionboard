"""Build the app's colour themes from Material Theme Builder exports.

    python tools/build_theme.py                 # every theme in themes/
    python tools/build_theme.py indigo          # only indigo
    python tools/build_theme.py vermellon --name success --color "#2FB37A" --name accent --color "#FF9F43"
    python tools/build_theme.py indigo --name info --color "#3B82F6"

A theme is two files in themes/:

- <name>.json: the JSON export from Material Theme Builder
  (https://material-foundation.github.io/material-theme-builder/), as is.
- <name>.extended.json: the extended (custom) colours, which Theme Builder
  shows but does not export. Created the first time the theme is built.
  "customColors" holds the colours typed into Theme Builder's "Custom colors"
  panel, by name (they do not depend on the theme's seed: they are not
  harmonized). Each --name/--color pair adds a colour to it or changes one,
  so the list can grow; the app needs "success" and "accent" (new files start
  with the defaults below). "light" and "dark" may hold the four roles of each
  colour (success, onSuccess, successContainer, onSuccessContainer…) copied
  from Theme Builder:

      {
          "customColors": {"success": "#2FB37A", "accent": "#FF9F43"},
          "light": {"success": "#266A4A", "onSuccess": "#FFFFFF", ...},
          "dark": {"success": "#90D5AD", "onSuccess": "#003822", ...}
      }

  Roles left out of "light"/"dark" are computed from "customColors" on every
  run, the way Theme Builder does for custom colours (tonal palette at chroma
  36, not harmonized), and written into the file under "computed" so it always
  shows what the app uses. "computed" belongs to the script: change a colour
  and it follows; paste a value into "light"/"dark" and that one wins. The
  computed values match Theme Builder's (checked for #2FB37A and #FF9F43).

Writes app/static/css/themes/<name>.css (the light scheme as --md-* custom
properties, plus --md-<colour>-custom with each custom colour as typed, read by
tokens.css) and themes.js (the list of themes, used by the wireframes' theme
switcher). Needs materialyoucolor (requirements-dev.txt).
"""

import argparse
import json
import re
import sys
from pathlib import Path

from materialyoucolor.hct import Hct
from materialyoucolor.palettes.tonal_palette import TonalPalette

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "themes"
OUT_DIR = ROOT / "app" / "static" / "css" / "themes"

# Custom colours the app uses (tokens.css), with the ones a new theme starts with
REQUIRED_CUSTOM_COLORS = {"success": "#2FB37A", "accent": "#FF9F43"}
COLOUR_NAME = re.compile(r"^[a-z][a-zA-Z0-9]*$")
HEX_COLOUR = re.compile(r"^#?[0-9a-fA-F]{6}$")
CUSTOM_CHROMA = 36
# role suffix → tone of a custom colour, per scheme
CUSTOM_TONES = {
    "light": {"": 40, "on": 100, "Container": 90, "onContainer": 30},
    "dark": {"": 80, "on": 20, "Container": 30, "onContainer": 90},
}


def argb(hex_colour: str) -> int:
    return 0xFF000000 | int(hex_colour.lstrip("#"), 16)


def hex_of(value: int) -> str:
    return f"#{value & 0xFFFFFF:06X}"


def kebab(role: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", role).lower()


def role_name(name: str, suffix: str) -> str:
    """("success", "onContainer") → "onSuccessContainer", Theme Builder's naming."""
    cap = name[0].upper() + name[1:]
    return {"": name, "on": f"on{cap}", "Container": f"{name}Container",
            "onContainer": f"on{cap}Container"}[suffix]


def read_extended(path: Path) -> dict:
    if path.is_file():
        return json.loads(path.read_text())
    print(f"created themes/{path.name}")
    return {"customColors": dict(REQUIRED_CUSTOM_COLORS)}


def set_custom_colours(extended: dict, colours: dict[str, str], file_name: str) -> None:
    """Add or change custom colours; say when pasted values will still win."""
    for name, colour in colours.items():
        extended.setdefault("customColors", {})[name] = colour
        pasted = [f"{scheme}.{role}" for scheme in CUSTOM_TONES
                  for role in (role_name(name, s) for s in CUSTOM_TONES[scheme])
                  if role in extended.get(scheme, {})]
        if pasted:
            print(f"{file_name}: {name} has pasted values that still win over {colour}:"
                  f" {', '.join(pasted)}")


def compute_roles(extended: dict, file_name: str) -> None:
    """Recompute, into "computed", every custom colour role not pasted in light/dark."""
    custom = extended.get("customColors", {})
    missing = [n for n in REQUIRED_CUSTOM_COLORS if n not in custom]
    if missing:
        sys.exit(f"{file_name}: the app needs {', '.join(missing)}"
                 f" (add it with --name {missing[0]} --color \"#RRGGBB\")")
    computed = {}
    for scheme, tones in CUSTOM_TONES.items():
        pasted = extended.get(scheme, {})
        for name, colour in custom.items():
            palette = TonalPalette.from_hue_and_chroma(Hct.from_int(argb(colour)).hue, CUSTOM_CHROMA)
            for suffix, tone in tones.items():
                role = role_name(name, suffix)
                if role not in pasted:
                    computed.setdefault(scheme, {})[role] = hex_of(palette.tone(tone))
    extended.pop("computed", None)
    if computed:
        extended["computed"] = computed


def build(name: str, colours: dict[str, str]) -> None:
    export_path = SOURCE_DIR / f"{name}.json"
    extended_path = SOURCE_DIR / f"{name}.extended.json"
    if not export_path.is_file():
        sys.exit(f"missing themes/{export_path.name} (the export from Material Theme Builder)")
    extended = read_extended(extended_path)
    set_custom_colours(extended, colours, extended_path.name)
    compute_roles(extended, extended_path.name)
    text = json.dumps(extended, indent=4) + "\n"
    if not extended_path.is_file() or extended_path.read_text() != text:
        extended_path.write_text(text)
    export = json.loads(export_path.read_text())
    custom = extended["customColors"]
    roles = {**export["schemes"]["light"], **extended.get("computed", {}).get("light", {}),
             **extended.get("light", {}), **{f"{n}Custom": c for n, c in custom.items()}}
    lines = [f"  --md-{kebab(role)}: {value.lower()};" for role, value in roles.items()]
    (OUT_DIR / f"{name}.css").write_text(
        f"/* Theme \"{name}\": generated by tools/build_theme.py from themes/{name}.json and"
        f" themes/{name}.extended.json (seed {export['seed']}). Do not edit by hand. */\n"
        ":root {\n" + "\n".join(lines) + "\n}\n")
    print(f"{name}: {len(roles)} roles; custom colours: "
          + ", ".join(f"{n} {c}" for n, c in custom.items()))


def write_list() -> None:
    names = sorted(p.stem for p in OUT_DIR.glob("*.css"))
    (OUT_DIR / "themes.js").write_text(
        "// Generated by tools/build_theme.py: the themes in this folder.\n"
        f"window.MISSIONBOARD_THEMES = {json.dumps(names)};\n")


def parse_args() -> tuple[list[str], dict[str, str]]:
    parser = argparse.ArgumentParser(
        description="Build app/static/css/themes/ from the Material Theme Builder exports in themes/.")
    parser.add_argument("themes", nargs="*", help="themes to build (default: all)")
    parser.add_argument("--name", action="append", default=[],
                        help="custom colour to add or change, e.g. success; pairs with the --color in the same position")
    parser.add_argument("--color", action="append", default=[], help='its colour, e.g. "#2FB37A"')
    args = parser.parse_args()
    if len(args.name) != len(args.color):
        parser.error("each --name needs its --color")
    if args.name and not args.themes:
        parser.error("say which theme the colours are for, e.g. build_theme.py vermellon --name ...")
    colours = {}
    for name, colour in zip(args.name, args.color):
        if not COLOUR_NAME.match(name):
            parser.error(f"--name {name}: letters and digits, starting with a lowercase letter (e.g. success, info2)")
        if not HEX_COLOUR.match(colour):
            parser.error(f'--color {colour}: a hex colour like "#2FB37A"')
        colours[name] = "#" + colour.lstrip("#").upper()
    return args.themes, colours


def main() -> None:
    themes, colours = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    themes = themes or sorted(
        p.stem for p in SOURCE_DIR.glob("*.json") if not p.name.endswith(".extended.json"))
    for name in themes:
        build(name, colours)
    write_list()


if __name__ == "__main__":
    main()
