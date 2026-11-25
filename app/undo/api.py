from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.children.repository import ChildrenRepository
from app.daily_prize.repository import PrizeSpinsRepository
from app.day_off.repository import DayOffsRepository
from app.deps import (
    get_clock,
    get_config_store,
    get_day_offs_repository,
    get_day_repository,
    get_event_log,
    get_image_libraries,
    get_prize_spins_repository,
    get_stars_repository,
    require_parent,
)
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.missions.repository import MissionsRepository
from app.settings import SettingsRepository
from app.stars.repository import StarsRepository
from app.storage.config_store import ConfigStore
from app.streaks.api import get_streaks_service
from app.streaks.service import StreaksService
from app.today.api import get_day_service
from app.today.repository import DayRepository
from app.today.service import DayService
from app.undo.service import UndoService

# Undoing a mission is for parents: with the code.
router = APIRouter(prefix="/api", tags=["undo"], dependencies=[Depends(require_parent)])


class UndoIn(BaseModel):
    keep_card: bool = False  # the gift card won that day stays theirs


def get_undo_service(
    store: ConfigStore = Depends(get_config_store),
    days: DayRepository = Depends(get_day_repository),
    day: DayService = Depends(get_day_service),
    stars: StarsRepository = Depends(get_stars_repository),
    spins: PrizeSpinsRepository = Depends(get_prize_spins_repository),
    streaks: StreaksService = Depends(get_streaks_service),
    offs: DayOffsRepository = Depends(get_day_offs_repository),
    clock=Depends(get_clock),
    events: EventLog = Depends(get_event_log),
) -> UndoService:
    return UndoService(
        ChildrenRepository(store),
        MissionsRepository(store),
        days,
        day,
        stars,
        spins,
        streaks,
        offs,
        SettingsRepository(store),
        clock,
        events,
    )


def _present(view: dict, libraries: ImageLibraries) -> dict:
    mission = view["mission"]
    return {
        "mission": {"id": mission.id, "name": mission.name, "image_url": libraries.url(mission.image)},
        "day": view["day"].isoformat(),
        "reopens": view["reopens"],
        "stars": view["stars"],
        "cards": view["cards"],
        "tank": view["tank"],
    }


@router.get("/children/{child_id}/missions/{mission_id}/days/{day}/undo")
def preview(
    child_id: str,
    mission_id: str,
    day: date,
    undo: UndoService = Depends(get_undo_service),
    libraries: ImageLibraries = Depends(get_image_libraries),
):
    """What undoing it would take with it (the window shows it before asking)."""
    return _present(undo.preview(child_id, mission_id, day), libraries)


@router.post("/children/{child_id}/missions/{mission_id}/days/{day}/undo")
def undo_mission(
    child_id: str,
    mission_id: str,
    day: date,
    body: UndoIn,
    undo: UndoService = Depends(get_undo_service),
    libraries: ImageLibraries = Depends(get_image_libraries),
):
    """«No la ha hecho»: the mission, its stars, the day's gift card and the tank, undone."""
    return _present(undo.undo(child_id, mission_id, day, body.keep_card), libraries)
