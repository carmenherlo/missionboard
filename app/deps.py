"""FastAPI dependencies shared by every feature.

create_app() builds the shared objects once and keeps them in app.state;
these functions hand them to the routes, and tests can override them.
"""

from fastapi import Depends, Header, HTTPException, Request

from app.clock import Clock
from app.events.repository import EventsRepository
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.parents.repository import ParentsRepository
from app.parents.service import ParentsService
from app.settings import SettingsRepository
from app.storage.config_store import ConfigStore
from app.songs.repository import SoundFiles
from app.storage.photo_store import PhotoStore


def get_config_store(request: Request) -> ConfigStore:
    return request.app.state.config_store


def get_photo_store(request: Request) -> PhotoStore:
    return request.app.state.photo_store


def get_sound_files(request: Request) -> SoundFiles:
    return request.app.state.sound_files


def get_clock(request: Request) -> Clock:
    return request.app.state.clock


def get_image_libraries(request: Request) -> ImageLibraries:
    return request.app.state.image_libraries


def get_event_log(
    request: Request,
    store: ConfigStore = Depends(get_config_store),
    clock: Clock = Depends(get_clock),
) -> EventLog:
    events: EventsRepository = request.app.state.events_repository
    return EventLog(events, clock, SettingsRepository(store))


def get_parents_service(
    store: ConfigStore = Depends(get_config_store),
    events: EventLog = Depends(get_event_log),
) -> ParentsService:
    return ParentsService(ParentsRepository(store), events)


def require_parent(
    x_parent_code: str | None = Header(default=None),
    parents: ParentsService = Depends(get_parents_service),
) -> None:
    """Dependency for endpoints only parents may call."""
    if not parents.is_valid_code(x_parent_code):
        raise HTTPException(status_code=401, detail="Invalid parent code")
