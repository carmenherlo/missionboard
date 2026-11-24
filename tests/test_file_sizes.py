"""A guard against files that keep growing: past a size, a file is usually doing
more than one job and should be split by responsibility.

Files already over the limit are listed with their size when the guard came in
(14/11/2026): they may shrink, never grow. When one is split below its limit,
its line here goes away.
"""

from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"

LIMITS = {".py": 300, ".js": 400, ".css": 400}

# Generated or third-party: not written by hand.
SKIPPED = ("static/libraries/", "static/css/themes/")

# Over the limit today; to split in the cleanup (1b–1d).
TOO_BIG = {
    "static/css/effects.css": 612,
    "static/css/routine.css": 432,
    "routines/api.py": 405,  # finishing went to control_api.py (18/11), what the screen gets to present.py (23/11)
    "missions/service.py": 377,
    "missions/api.py": 358,  # +1 import line when routines/repository.py was split (1d)
    "routines/editor.py": 323,
}

# Over the limit on purpose: every user-facing text in one place (decided 14/11).
ALLOWED = {"static/js/texts.js"}


def _sizes() -> dict[str, int]:
    sizes = {}
    for path in APP_DIR.rglob("*"):
        name = path.relative_to(APP_DIR).as_posix()
        if path.suffix in LIMITS and path.is_file() and not name.startswith(SKIPPED):
            sizes[name] = len(path.read_text().splitlines())
    return sizes


def test_no_file_grows_past_its_limit():
    sizes = _sizes()
    too_big = [
        f"{name}: {lines} lines (limit {TOO_BIG.get(name, LIMITS[Path(name).suffix])})"
        for name, lines in sorted(sizes.items())
        if name not in ALLOWED and lines > TOO_BIG.get(name, LIMITS[Path(name).suffix])
    ]
    assert not too_big, "Split by responsibility instead of growing:\n" + "\n".join(too_big)


def test_the_list_of_big_files_is_up_to_date():
    """A file that was split (or removed) leaves the list, so it cannot grow back."""
    sizes = _sizes()
    stale = [name for name in TOO_BIG if sizes.get(name, 0) <= LIMITS[Path(name).suffix]]
    assert not stale, f"Remove from TOO_BIG: {stale}"
