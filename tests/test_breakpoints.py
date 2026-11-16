"""The screen widths where the layout changes, the same in every CSS file.

CSS cannot use a variable inside @media, so each width is written where it is used;
this guard keeps them to this short list (decided 16/11/2026: no build step for it).
A "max-width" is the width minus 0.02px, so the two sides never overlap.
"""

import re
from pathlib import Path

CSS_DIR = Path(__file__).resolve().parent.parent / "app" / "static" / "css"

BREAKPOINTS = {
    600: "a phone: one column where the tablet has two",
    860: "two columns of panels in the parents' screens",
    1000: "the parents' menu always open on a side",
}

WIDTH = re.compile(r"\((min|max)-width:\s*([\d.]+)px\)")


def allowed(kind: str, value: float) -> bool:
    return any(value == (width if kind == "min" else width - 0.02) for width in BREAKPOINTS)


def test_every_media_query_uses_a_known_width():
    wrong = []
    for css in sorted(CSS_DIR.glob("*.css")):
        for number, line in enumerate(css.read_text(encoding="utf-8").splitlines(), start=1):
            if "@media" not in line:
                continue
            for kind, value in WIDTH.findall(line):
                if not allowed(kind, float(value)):
                    wrong.append(f"{css.name}:{number}: {line.strip()}")
    assert not wrong, "use one of the widths in BREAKPOINTS (max-width: N - 0.02px):\n" + "\n".join(wrong)
