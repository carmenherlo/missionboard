"""A routine that rings at a time, started by hand for a while: its times are put away,
and back to ringing at a time they come back (the pinned one stays put; if its parts
changed meanwhile, the routine grows or shrinks from it, see timing.settled)."""

from pydantic import BaseModel, ConfigDict, Field

from app.routines.repository import NEW_PART_MINUTES
from app.routines.timing import hhmm, minute_of
from app.settings import TIME


class SavedTimes(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    wake: str = Field(pattern=TIME)
    anchor: str = "start"
    first_at: str | None = Field(default=None, pattern=TIME)  # when its first part started
    goal_at: str | None = Field(default=None, pattern=TIME)  # its goal ("Termina a las": the pinned time)
    offsets: dict[str, int] = {}
    notices: list[dict] = []


def put_away(doc: dict) -> dict:
    """The routine's times, kept while it is started by hand."""
    return SavedTimes(
        wake=doc["wake"],
        anchor=doc.get("anchor", "start"),
        first_at=doc["parts"][0].get("at"),
        goal_at=(doc.get("goal") or {}).get("at"),
        offsets=doc.get("offsets", {}),
        notices=doc.get("notices", []),
    ).model_dump(mode="json")


def brought_back(doc: dict, saved: dict) -> dict:
    """The changes to ring at its times again (the pinned time from the saved ones)."""
    times = SavedTimes.model_validate(saved)
    ends = times.anchor == "end" and doc.get("goal") and times.goal_at  # its goal may be gone
    parts = [dict(part) for part in doc["parts"]]
    parts[0]["at"] = times.first_at or times.wake
    changes = {
        "wake": times.wake,
        "anchor": "end" if ends else "start",
        "parts": parts,
        "offsets": times.offsets,
        "notices": times.notices,
        "timed": None,
    }
    if ends:
        changes["goal"] = {**doc["goal"], "at": times.goal_at}
    return changes


def switched(doc: dict, wake: str | None) -> dict:
    """The changes when a routine goes from ringing at a time to started by hand, or back."""
    manual = doc.get("wake") is None
    if wake is None and not manual:  # by hand: parts one after the other; the goal after them
        parts = [{**part, "at": None} for part in doc["parts"]]
        return {"parts": parts, "offsets": {}, "notices": [], "anchor": "start", "timed": put_away(doc)}
    if wake is None or not manual:
        return {}
    if doc.get("timed"):
        return brought_back(doc, doc["timed"])
    parts = [dict(part) for part in doc["parts"]]
    parts[0]["at"] = hhmm((minute_of(wake) + NEW_PART_MINUTES) % (24 * 60))
    return {"parts": parts}
