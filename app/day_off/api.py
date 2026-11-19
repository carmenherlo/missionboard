from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.children.repository import ChildrenRepository
from app.day_off.repository import DayOffsRepository
from app.day_off.service import DayOffService
from app.deps import (
    get_clock,
    get_config_store,
    get_day_offs_repository,
    get_event_log,
    get_image_libraries,
    require_parent,
)
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.missions.repository import MissionsRepository
from app.settings import SettingsRepository
from app.storage.config_store import ConfigStore

# Letting a child off is for parents: with the code.
router = APIRouter(prefix="/api", tags=["day_off"], dependencies=[Depends(require_parent)])


class DayOffIn(BaseModel):
    whole: bool = False
    missions: list[str] = Field(default_factory=list, max_length=50)
    phrase: str = Field(default="", max_length=80)


def get_day_off_service(
    store: ConfigStore = Depends(get_config_store),
    offs: DayOffsRepository = Depends(get_day_offs_repository),
    clock=Depends(get_clock),
    events: EventLog = Depends(get_event_log),
) -> DayOffService:
    return DayOffService(
        ChildrenRepository(store), MissionsRepository(store), offs, SettingsRepository(store), clock, events
    )


def _present(view: dict, libraries: ImageLibraries) -> dict:
    return {
        "day": view["day"].isoformat(),
        "whole": view["whole"],
        "phrase": view["phrase"],
        "missions": [
            {"id": m.id, "name": m.name, "image_url": libraries.url(m.image), "off": off} for m, off in view["missions"]
        ],
    }


@router.get("/children/{child_id}/day-offs/{day}")
def get_day_off(
    child_id: str,
    day: date,
    offs: DayOffService = Depends(get_day_off_service),
    libraries: ImageLibraries = Depends(get_image_libraries),
):
    """What the child has that day and what of it is let off ("Hoy no puede…")."""
    return _present(offs.day(child_id, day), libraries)


@router.put("/children/{child_id}/day-offs/{day}")
def set_day_off(
    child_id: str,
    day: date,
    body: DayOffIn,
    offs: DayOffService = Depends(get_day_off_service),
    libraries: ImageLibraries = Depends(get_image_libraries),
):
    """The whole day, or some missions of it, let off, with an optional sentence for the voice."""
    return _present(offs.set_day(child_id, day, body.whole, body.missions, body.phrase), libraries)
