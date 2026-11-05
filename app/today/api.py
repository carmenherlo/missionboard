from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.children import avatars
from app.children.api import public_child
from app.children.repository import ChildrenRepository
from app.deps import get_clock, get_config_store, get_event_log, get_image_libraries
from app.errors import NotFoundError
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.missions.repository import MissionsRepository
from app.prizes.repository import PrizesRepository
from app.routines.repository import RoutinesRepository
from app.settings import SettingsRepository
from app.storage.config_store import ConfigStore
from app.today.repository import BackgroundStore, DayRepository
from app.today.service import NOTES, DayService, Today

# The children's zone: no parent code.
router = APIRouter(prefix="/api", tags=["today"])

STAR_IMAGE = "fluent/star"
CELEBRATION_STAR_IMAGE = "fluent/glowing-star"
PRIZE_IMAGE = "fluent/wrapped-gift"


class StepIn(BaseModel):
    checked: bool


class NoteIn(BaseModel):
    kind: Literal[NOTES]
    mission_id: str | None = Field(default=None, pattern=r"^[\w-]{1,64}$")
    step_id: str | None = Field(default=None, pattern=r"^[\w-]{1,64}$")


def get_day_repository(request: Request) -> DayRepository:
    return request.app.state.day_repository


def get_background_store(request: Request) -> BackgroundStore:
    return request.app.state.background_store


def get_day_service(
    store: ConfigStore = Depends(get_config_store),
    days: DayRepository = Depends(get_day_repository),
    clock=Depends(get_clock),
    events: EventLog = Depends(get_event_log),
) -> DayService:
    return DayService(
        ChildrenRepository(store), MissionsRepository(store), days, SettingsRepository(store), clock, events,
        PrizesRepository(store), RoutinesRepository(store),
    )


class Presenter:
    """Turns a child's day into JSON, with the address of every image."""

    def __init__(
        self,
        libraries: ImageLibraries = Depends(get_image_libraries),
        backgrounds: BackgroundStore = Depends(get_background_store),
    ):
        self._libraries = libraries
        self._backgrounds = backgrounds

    def __call__(self, today: Today) -> dict:
        moment = today.moment.name
        version = self._backgrounds.version(moment)
        return {
            "child": public_child(today.child),
            "colors": avatars.tones(today.child.color),
            "day": today.day.isoformat(),
            "moment": moment,
            "background_url": f"api/backgrounds/{moment}?v={version}" if version else None,
            "stars": today.stars,
            "star_url": self._libraries.url(STAR_IMAGE),
            "celebration_star_url": self._libraries.url(CELEBRATION_STAR_IMAGE),
            "focus_is_now": today.focus_is_now,
            "missions": [
                {
                    "id": item.mission.id,
                    "name": item.mission.name,
                    "image_url": self._libraries.url(item.mission.image),
                    "state": item.state,
                    "focus": item.focus,
                    "schedule": (  # today's: its own, or its routine's (rutinas-8)
                        {"start": item.schedule.start, "end": item.schedule.end}
                        if item.schedule else None
                    ),
                    "steps": [
                        {
                            "id": step.id,
                            "text": step.text,
                            "image_url": self._libraries.url(step.image),
                            "checked": item.state == "done" or step.id in item.checked,
                        }
                        for step in item.mission.steps
                    ],
                }
                for item in today.missions
            ],
            "prize": self._prize(today),
        }

    def _prize(self, today: Today) -> dict | None:
        prize = today.prize
        if prize is None:
            return None
        return {
            "state": prize.state,
            "image_url": self._libraries.url(PRIZE_IMAGE),
            "spins_left": prize.spins_left,
            "won": [{**w, "image_url": self._libraries.url(w["image"])} for w in prize.won],
            "wheel": [
                {"id": p.id, "text": p.text, "image_url": self._libraries.url(p.image)} for p in prize.prizes
            ],
        }


@router.get("/children/{child_id}/today")
def get_today(child_id: str, days: DayService = Depends(get_day_service), present: Presenter = Depends()):
    return present(days.today(child_id))


@router.put("/children/{child_id}/today/missions/{mission_id}/steps/{step_id}")
def set_step(
    child_id: str,
    mission_id: str,
    step_id: str,
    body: StepIn,
    days: DayService = Depends(get_day_service),
    present: Presenter = Depends(),
):
    """Check or uncheck a step; says whether that completed the mission."""
    result = days.set_step(child_id, mission_id, step_id, body.checked)
    return {"completed": result.completed, "stars_earned": result.stars_earned, "today": present(result.today)}


@router.post("/children/{child_id}/today/prize/spin")
def spin(child_id: str, days: DayService = Depends(get_day_service), present: Presenter = Depends()):
    """Spin the wheel: says which prize came out; the screen turns the wheel to it."""
    result = days.spin(child_id)
    return {"prize_id": result.prize.id, "today": present(result.today)}


@router.post("/children/{child_id}/today/notes", status_code=204)
def note(child_id: str, body: NoteIn, days: DayService = Depends(get_day_service)) -> None:
    days.note(child_id, body.kind, body.mission_id, body.step_id)


@router.get("/backgrounds/{name}")
def background(name: str, backgrounds: BackgroundStore = Depends(get_background_store)):
    path = backgrounds.path(name) if name.replace("-", "").isalnum() else None
    if path is None:
        raise NotFoundError("Background not found")
    return FileResponse(path)
