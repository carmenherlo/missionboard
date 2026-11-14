from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.children.repository import ChildrenRepository
from app.deps import get_clock, get_config_store, get_event_log, get_stars_repository, require_parent
from app.events.service import EventLog
from app.settings import SettingsRepository
from app.stars.repository import StarsRepository
from app.stars.service import StarsService
from app.storage.config_store import ConfigStore

router = APIRouter(prefix="/api", tags=["stars"], dependencies=[Depends(require_parent)])

MAX_GIFT = 50  # stars a parent can give (or take) at once


class GiftIn(BaseModel):
    stars: int = Field(ge=1, le=MAX_GIFT)


def get_stars_service(
    store: ConfigStore = Depends(get_config_store),
    stars: StarsRepository = Depends(get_stars_repository),
    clock=Depends(get_clock),
    events: EventLog = Depends(get_event_log),
) -> StarsService:
    return StarsService(ChildrenRepository(store), stars, SettingsRepository(store), clock, events)


@router.get("/children/{child_id}/stars")
def child_stars(child_id: str, stars: StarsService = Depends(get_stars_service)):
    return {"stars": stars.balance(child_id)}


@router.post("/children/{child_id}/stars/take")
def take_stars(child_id: str, body: GiftIn, stars: StarsService = Depends(get_stars_service)):
    """A parent takes some stars away (Padres · Niño); 422 if they do not have that many."""
    return {"stars": stars.take(child_id, body.stars)}


@router.post("/children/{child_id}/stars/gift")
def give_stars(child_id: str, body: GiftIn, stars: StarsService = Depends(get_stars_service)):
    """A parent gives the child some stars (Padres · Niño)."""
    return {"stars": stars.give(child_id, body.stars)}
