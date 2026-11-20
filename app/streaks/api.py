from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.children.repository import ChildrenRepository
from app.day_off.repository import DayOffsRepository
from app.deps import (
    get_clock,
    get_config_store,
    get_day_offs_repository,
    get_day_repository,
    get_event_log,
    get_image_libraries,
    get_streaks_repository,
    require_parent,
)
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.missions.repository import MissionsRepository
from app.settings import SettingsRepository
from app.storage.config_store import ConfigStore
from app.streaks.repository import StreaksRepository
from app.streaks.service import StreaksService
from app.today.repository import DayRepository

# The child's week has no parent code; letting a day off has.
router = APIRouter(prefix="/api", tags=["streaks"])


def get_streaks_service(
    store: ConfigStore = Depends(get_config_store),
    days: DayRepository = Depends(get_day_repository),
    streaks: StreaksRepository = Depends(get_streaks_repository),
    clock=Depends(get_clock),
    events: EventLog = Depends(get_event_log),
    offs: DayOffsRepository = Depends(get_day_offs_repository),
) -> StreaksService:
    return StreaksService(
        ChildrenRepository(store),
        MissionsRepository(store),
        days,
        streaks,
        SettingsRepository(store),
        clock,
        events,
        offs,
    )


def present_week(view: dict | None, libraries: ImageLibraries | None = None) -> dict:
    """The week for the child's screen and the parents' cards; {"on": False} while rachas are off."""
    if view is None:
        return {"on": False}
    week, result, loaded = view["week"], view["result"], view.get("loaded", set())

    def tanks(week) -> list[dict]:
        return [
            {"day": t.day.isoformat(), "letter": t.letter, "state": t.state, "loaded": t.day.isoformat() in loaded}
            for t in week.tanks
        ]

    today = view.get("today")
    won = bool(result and result["tier"] != "none")
    return {
        "on": True,
        # Seen only on a day that counts (today has a tank), or while a won week's rocket
        # waits to take off: on the days off (the weekend) the week stays out of sight.
        # The tanks are those of the week shown: this one, or the one just closed until
        # the next one starts (streaks/week.py).
        "shown": won or any(t.day == today for t in week.tanks),
        "end": week.end.isoformat(),
        "took_off": view.get("took_off", False),
        "tanks": tanks(week),
        # The next day that counts: the workshop rests till then.
        "next_day": view["next_day"].isoformat() if view.get("next_day") else None,
        "full": week.full,
        "counted": week.counted,
        "result": result
        and {
            "end": result["week_end"],
            "tier": result["tier"],
            "prize_text": result["prize_text"],
            "full": result["full_days"],
            "counted": result["days"],
            **({"prize_image_url": libraries.url(result.get("prize_image"))} if libraries else {}),
        },
    }


@router.get("/children/{child_id}/week")
def get_week(
    child_id: str,
    streaks: StreaksService = Depends(get_streaks_service),
    libraries: ImageLibraries = Depends(get_image_libraries),
):
    return present_week(streaks.week(child_id), libraries)


@router.post("/children/{child_id}/week/fuel/{day}")
def load_fuel(
    child_id: str,
    day: date,
    streaks: StreaksService = Depends(get_streaks_service),
    libraries: ImageLibraries = Depends(get_image_libraries),
):
    """The child loads a full tank into the rocket, in the workshop (taller.html)."""
    return present_week(streaks.load_fuel(child_id, day), libraries)


@router.post("/children/{child_id}/week/{end}/seen", status_code=204)
def week_seen(child_id: str, end: str, streaks: StreaksService = Depends(get_streaks_service)) -> None:
    """The child has seen how that week ended (the rocket took off, or not)."""
    streaks.week_seen(child_id, end)


class FreeDayIn(BaseModel):
    free: bool


@router.put("/children/{child_id}/free-days/{day}", status_code=204, dependencies=[Depends(require_parent)])
def free_day(child_id: str, day: date, body: FreeDayIn, streaks: StreaksService = Depends(get_streaks_service)) -> None:
    """A parent lets a whole day off: it neither counts nor breaks the week (day_off/ does the rest)."""
    streaks.set_free_day(child_id, day, body.free)
