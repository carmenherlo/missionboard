from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.children import avatars
from app.children.api import public_child
from app.children.repository import ChildrenRepository
from app.deps import get_clock, get_config_store, get_event_log, get_image_libraries, require_parent
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.missions.repository import ChildTask, MissionsRepository
from app.prizes.repository import PrizesRepository
from app.routines.repository import RoutinesRepository
from app.settings import SettingsRepository
from app.storage.config_store import ConfigStore
from app.today.repository import DayRepository
from app.today.service import NOTES, DayService, MissionToday, Today

# The children's zone: no parent code.
router = APIRouter(prefix="/api", tags=["today"])

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
STAR_IMAGE = "fluent/star"
MAX_GIFT = 50  # stars a parent can give at once
CELEBRATION_STAR_IMAGE = "fluent/glowing-star"
PRIZE_IMAGE = "fluent/wrapped-gift"
FIRE_IMAGE = "fluent/fire"  # the streak (step 8)


class StepIn(BaseModel):
    checked: bool


class NoteIn(BaseModel):
    kind: Literal[NOTES]
    mission_id: str | None = Field(default=None, pattern=r"^[\w-]{1,64}$")
    step_id: str | None = Field(default=None, pattern=r"^[\w-]{1,64}$")


def get_day_repository(request: Request) -> DayRepository:
    return request.app.state.day_repository


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


def background_url(season: str, moment: str) -> str | None:
    """The app's own pictures (static/backgrounds/); if one is missing, none is shown."""
    relative = f"backgrounds/{season}/{moment}.webp"
    return f"static/{relative}" if (STATIC_DIR / relative).is_file() else None


class Presenter:
    """Turns a child's day into JSON, with the address of every image."""

    def __init__(self, libraries: ImageLibraries = Depends(get_image_libraries),
                 store: ConfigStore = Depends(get_config_store)):
        self._libraries = libraries
        self._store = store

    def __call__(self, today: Today) -> dict:
        return {
            "child": public_child(today.child),
            "colors": avatars.tones(today.child.color),
            "day": today.day.isoformat(),
            "moment": today.moment,
            "background_url": background_url(today.season.name, today.moment),
            "stars": today.stars,
            "streak": today.streak,
            "fire_url": self._libraries.url(FIRE_IMAGE),
            "star_url": self._libraries.url(STAR_IMAGE),
            "celebration_star_url": self._libraries.url(CELEBRATION_STAR_IMAGE),
            "focus_is_now": today.focus_is_now,
            "route_look": SettingsRepository(self._store).settings().route.model_dump(mode="json"),
            "missions": [
                {
                    "id": item.mission.id,
                    "name": item.mission.name,
                    "image_url": self._libraries.url(item.mission.image),
                    "colors": avatars.tones(item.mission.color),
                    "state": item.state,
                    "focus": item.focus,
                    "schedule": (  # today's: its own, or its routine's (rutinas-8)
                        {"start": item.schedule.start, "end": item.schedule.end}
                        if item.schedule else None
                    ),
                    "total": len(item.marks),
                    "done": len(item.marks) if item.state == "done" else len(item.checked),
                    "tasks": [self._task(item, task) for task in item.tasks],
                }
                for item in today.missions
            ],
            "prize": self._prize(today),
        }

    def _task(self, item: MissionToday, task: ChildTask) -> dict:
        """A task for its card: the child checks the card; its steps are reminders."""
        done = item.state == "done"
        return {
            "id": task.task.id,
            "text": task.task.text,
            "image_url": self._libraries.url(task.task.image),
            "checked": done or task.task.id in item.checked,
            "steps": [
                {"id": s.id, "text": s.text, "image_url": self._libraries.url(s.image)}
                for s in task.steps
            ],
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


@router.put("/children/{child_id}/today/missions/{mission_id}/marks/{item_id}")
def set_mark(
    child_id: str,
    mission_id: str,
    item_id: str,
    body: StepIn,
    days: DayService = Depends(get_day_service),
    present: Presenter = Depends(),
):
    """Check or uncheck a step (or a task without steps); says whether that completed the mission."""
    result = days.set_mark(child_id, mission_id, item_id, body.checked)
    return {"completed": result.completed, "stars_earned": result.stars_earned, "today": present(result.today)}


@router.post("/children/{child_id}/today/missions/{mission_id}/open", dependencies=[Depends(require_parent)])
def open_today(child_id: str, mission_id: str, days: DayService = Depends(get_day_service),
               present: Presenter = Depends()):
    """A parent opens a closed or upcoming mission, only today (holding it on the route)."""
    return present(days.open_today(child_id, mission_id))


class GiftIn(BaseModel):
    stars: int = Field(ge=1, le=MAX_GIFT)


@router.get("/children/{child_id}/stars", dependencies=[Depends(require_parent)])
def child_stars(child_id: str, days: DayService = Depends(get_day_service)):
    return {"stars": days.stars(child_id)}


@router.post("/children/{child_id}/stars/take", dependencies=[Depends(require_parent)])
def take_stars(child_id: str, body: GiftIn, days: DayService = Depends(get_day_service)):
    """A parent takes some stars away (Padres · Niño); 422 if they do not have that many."""
    return {"stars": days.take_stars(child_id, body.stars)}


@router.post("/children/{child_id}/stars/gift", dependencies=[Depends(require_parent)])
def give_stars(child_id: str, body: GiftIn, days: DayService = Depends(get_day_service)):
    """A parent gives the child some stars (Editar niño → Estrellas)."""
    return {"stars": days.give_stars(child_id, body.stars)}


@router.post("/children/{child_id}/today/prize/spin")
def spin(child_id: str, days: DayService = Depends(get_day_service), present: Presenter = Depends()):
    """Spin the wheel: says which prize came out; the screen turns the wheel to it."""
    result = days.spin(child_id)
    return {"prize_id": result.prize.id, "today": present(result.today)}


@router.post("/children/{child_id}/today/notes", status_code=204)
def note(child_id: str, body: NoteIn, days: DayService = Depends(get_day_service)) -> None:
    days.note(child_id, body.kind, body.mission_id, body.step_id)
