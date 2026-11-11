from dataclasses import asdict

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, field_validator

from app.avatars.repository import AvatarsRepository
from app.children.repository import Child, ChildrenRepository
from app.children.service import ChildData, ChildrenService
from app.clock import app_day
from app.deps import get_clock, get_config_store, get_event_log, get_photo_store, require_parent
from app.events.service import EventLog
from app.missions.api import get_missions_service
from app.missions.repository import MissionsRepository
from app.missions.service import MissionsService
from app.routines.editor import RoutinesEditor
from app.routines.repository import RoutinesRepository
from app.settings import SettingsRepository
from app.storage.config_store import ConfigStore
from app.storage.photo_store import PhotoStore

router = APIRouter(prefix="/api", tags=["children"])


class ChildIn(BaseModel):
    name: str = Field(max_length=30)
    preset: str

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be empty")
        return value


def get_children_service(
    request: Request,
    store: ConfigStore = Depends(get_config_store),
    photos: PhotoStore = Depends(get_photo_store),
    missions: MissionsService = Depends(get_missions_service),
    events: EventLog = Depends(get_event_log),
    clock=Depends(get_clock),
) -> ChildrenService:
    routines = RoutinesEditor(RoutinesRepository(store), ChildrenRepository(store), MissionsRepository(store), events)
    settings = SettingsRepository(store).settings()

    def welcome(child: Child) -> None:
        now = clock.now()
        request.app.state.day_repository.add_starting_stars(
            child, settings.starting_stars, app_day(now, settings.day_starts_at), now)

    return ChildrenService(ChildrenRepository(store), photos, events, dependents=[missions, routines], welcome=welcome,
                           family_avatars=AvatarsRepository(store))


def public_child(child: Child) -> dict:
    """A child as the screens get it."""
    return asdict(child)


@router.get("/children")
def list_children(children: ChildrenService = Depends(get_children_service)):
    return [public_child(child) for child in children.list()]


@router.post("/children", status_code=201, dependencies=[Depends(require_parent)])
def create_child(body: ChildIn, children: ChildrenService = Depends(get_children_service)):
    return public_child(children.create(ChildData(**body.model_dump())))


@router.put("/children/{child_id}", dependencies=[Depends(require_parent)])
def update_child(
    child_id: str, body: ChildIn, children: ChildrenService = Depends(get_children_service)
):
    return public_child(children.update(child_id, ChildData(**body.model_dump())))


@router.delete("/children/{child_id}", status_code=204, dependencies=[Depends(require_parent)])
def delete_child(child_id: str, children: ChildrenService = Depends(get_children_service)) -> None:
    children.delete(child_id)
