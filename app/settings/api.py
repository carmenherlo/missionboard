from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.clock import Clock, app_day
from app.deps import get_clock, get_config_store, get_event_log, require_parent
from app.events.service import EventLog
from app.settings.repository import HomeLook, RouteLook, Season, SettingsRepository, ShopNotify
from app.settings.service import SettingsService
from app.storage.config_store import ConfigStore
from app.today.api import background_url
from app.today.service import current_moment, current_season

router = APIRouter(prefix="/api/settings", tags=["settings"], dependencies=[Depends(require_parent)])
# The children's home screen reads how it looks: no parent code.
home_router = APIRouter(prefix="/api/home", tags=["settings"])


class SettingsPatch(BaseModel):
    """What the parents' screens change; the values are checked by Settings itself."""

    stars_per_mission: int | None = None
    daily_prize_spins: int | None = None
    starting_stars: int | None = None
    day_starts_at: str | None = None
    seasons: list[Season] | None = None
    home: HomeLook | None = None
    route: RouteLook | None = None
    shop_notify: ShopNotify | None = None
    streak_rule: str | None = None
    routine_warn_minutes: int | None = None


class FeaturesPatch(BaseModel):
    model_config = ConfigDict(strict=True)  # true or false, never "no"
    # Only the switches that do something today (ajustes.html, question 3).
    daily_prize: bool | None = None
    shop: bool | None = None
    streaks: bool | None = None
    routines: bool | None = None


def get_settings_service(
    store: ConfigStore = Depends(get_config_store), events: EventLog = Depends(get_event_log)
) -> SettingsService:
    return SettingsService(SettingsRepository(store), events)


def _now(settings, clock: Clock) -> dict:
    """The season and the moment of the day now, and its picture."""
    now = clock.now()
    season = current_season(settings.seasons, app_day(now, settings.day_starts_at))
    moment = current_moment(season, now.strftime("%H:%M"))
    return {"season": season.name, "moment": moment, "background_url": background_url(season.name, moment)}


def _present(service: SettingsService, clock: Clock) -> dict:
    settings = service.settings()
    return {
        "settings": settings.model_dump(mode="json"),
        "features": service.features().model_dump(mode="json"),
        "now": _now(settings, clock),
    }


def _given(body: BaseModel) -> dict:
    return {name: getattr(body, name) for name in body.model_fields_set if getattr(body, name) is not None}


@router.get("")
def get_settings(service: SettingsService = Depends(get_settings_service), clock: Clock = Depends(get_clock)):
    return _present(service, clock)


@router.patch("")
def update_settings(body: SettingsPatch, service: SettingsService = Depends(get_settings_service),
                    clock: Clock = Depends(get_clock)):
    service.update_settings(_given(body))
    return _present(service, clock)


@router.patch("/features")
def update_features(body: FeaturesPatch, service: SettingsService = Depends(get_settings_service),
                    clock: Clock = Depends(get_clock)):
    service.update_features(_given(body))
    return _present(service, clock)


@router.post("/seasons/reset")
def reset_seasons(service: SettingsService = Depends(get_settings_service), clock: Clock = Depends(get_clock)):
    service.reset_seasons()
    return _present(service, clock)


@router.post("/home/reset")
def reset_home(service: SettingsService = Depends(get_settings_service), clock: Clock = Depends(get_clock)):
    service.reset_home()
    return _present(service, clock)


@router.post("/route/reset")
def reset_route(service: SettingsService = Depends(get_settings_service), clock: Clock = Depends(get_clock)):
    service.reset_route()
    return _present(service, clock)


@home_router.get("")
def home_look(store: ConfigStore = Depends(get_config_store), clock: Clock = Depends(get_clock)):
    """How the home screen looks, and the picture of the moment for its background."""
    settings = SettingsRepository(store).settings()
    return {"look": settings.home.model_dump(mode="json"), "background_url": _now(settings, clock)["background_url"]}
