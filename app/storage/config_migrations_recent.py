"""The config.yaml migrations from version 27 on (see config_migrations.py): each one takes
the document at N and returns it at N + 1, frozen with the values of its time."""

from collections.abc import Callable

RECENT: dict[int, Callable[[dict], dict]] = {}


def _v27_to_v28(doc: dict) -> dict:
    """The day always starts at 00:00 (misiones-para-quien.html, 27/11): its setting goes."""
    (doc.get("settings") or {}).pop("day_starts_at", None)
    doc["version"] = 28
    return doc


RECENT[27] = _v27_to_v28


def _v28_to_v29(doc: dict) -> dict:
    """Who a mission is for (misiones-para-quien.html, 27/11): the children who saw any task
    of it. Tasks are switched on and off whole: one with any step on stays on, steps go."""
    child_ids = [child["id"] for child in doc.get("children") or []]
    for mission in doc.get("missions") or []:
        off = mission.get("off") or {}
        hidden = {
            child: {
                t["id"]
                for t in mission.get("tasks") or []
                if {t["id"], *(s["id"] for s in t.get("steps") or [])} <= set(ids)
            }
            for child, ids in off.items()
        }
        tasks = [t["id"] for t in mission.get("tasks") or []]
        mission["kids"] = [c for c in child_ids if not tasks or set(tasks) - hidden.get(c, set())]
        mission["off"] = {c: [t for t in tasks if t in hidden[c]] for c in mission["kids"] if hidden.get(c)}
    doc["version"] = 29
    return doc


RECENT[28] = _v28_to_v29


def _v29_to_v30(doc: dict) -> dict:
    """The routine, inside its mission (rutina-en-mision.html, 27/11): no switch for every
    routine (switched off, each one is kept off), and its children are some of its mission's,
    listed (none listed meant every child)."""
    all_on = (doc.get("features") or {}).pop("routines", True)
    children = [child["id"] for child in doc.get("children") or []]
    kids_of = {m["id"]: m.get("kids") or [] for m in doc.get("missions") or []}
    for routine in doc.get("routines") or []:
        mission_kids = kids_of.get(routine.get("mission_id"), [])
        routine["kids"] = [k for k in routine.get("kids") or children if k in mission_kids]
        if not all_on:
            routine["off"] = True
    doc["version"] = 30
    return doc


RECENT[29] = _v29_to_v30
