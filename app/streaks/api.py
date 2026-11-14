from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.children.repository import ChildrenRepository
from app.deps import (
    get_clock,
    get_config_store,
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
) -> StreaksService:
    return StreaksService(
        ChildrenRepository(store), MissionsRepository(store), days, streaks, SettingsRepository(store), clock, events
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

    launch = view.get("launch")
    return {
        "on": True,
        "end": week.end.isoformat(),
        "tanks": tanks(week),
        # The week whose rocket is ready to take off (or not), with a result not seen yet.
        "launch_tanks": tanks(launch) if launch else None,
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
    """A parent lets a day off (ill, away): it neither counts nor breaks the week."""
    streaks.set_free_day(child_id, day, body.free)
