"""FastAPI dependencies shared by every feature.

create_app() builds the shared objects once and keeps them in app.state;
these functions hand them to the routes, and tests can override them.
"""

from fastapi import Depends, Header, HTTPException, Request

from app.avatars.repository import AvatarFiles
from app.clock import Clock
from app.daily_prize.repository import PrizeSpinsRepository
from app.day_marks.repository import DaySnapshotsRepository
from app.day_off.repository import DayOffsRepository
from app.events.repository import EventsRepository
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.parents.repository import ParentsRepository
from app.parents.service import ParentsService
from app.routines.races_repository import RacesRepository
from app.songs.repository import SoundFiles
from app.stars.repository import StarsRepository
from app.storage.config_store import ConfigStore
from app.storage.photo_store import PhotoStore
from app.streaks.repository import StreaksRepository
from app.today.repository import DayRepository
from app.vouchers.repository import MomentsRepository


def get_config_store(request: Request) -> ConfigStore:
    return request.app.state.config_store


def get_photo_store(request: Request) -> PhotoStore:
    return request.app.state.photo_store


def get_sound_files(request: Request) -> SoundFiles:
    return request.app.state.sound_files


def get_avatar_files(request: Request) -> AvatarFiles:
    return request.app.state.avatar_files


def get_day_repository(request: Request) -> DayRepository:
    """What each child has done each day (shared by the day and the rachas)."""
    return request.app.state.day_repository


def get_stars_repository(request: Request) -> StarsRepository:
    return request.app.state.stars_repository


def get_prize_spins_repository(request: Request) -> PrizeSpinsRepository:
    return request.app.state.prize_spins_repository


def get_streaks_repository(request: Request) -> StreaksRepository:
    return request.app.state.streaks_repository


def get_day_offs_repository(request: Request) -> DayOffsRepository:
    """Días libres: read by the day, the prize, the rachas and the routines."""
    return request.app.state.day_offs_repository


def get_day_snapshots_repository(request: Request) -> DaySnapshotsRepository:
    """How the app had left a day before a parent changed it (day_marks/)."""
    return request.app.state.day_snapshots_repository


def get_races_repository(request: Request) -> RacesRepository:
    """Races (modo-carrera.html): read by the routines and the day (a lost race closes its mission)."""
    return request.app.state.races_repository


def get_moments_repository(request: Request) -> MomentsRepository:
    return request.app.state.moments_repository


def get_clock(request: Request) -> Clock:
    return request.app.state.clock


def get_image_libraries(request: Request) -> ImageLibraries:
    return request.app.state.image_libraries


def get_event_log(
    request: Request,
    clock: Clock = Depends(get_clock),
) -> EventLog:
    events: EventsRepository = request.app.state.events_repository
    return EventLog(events, clock)


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
