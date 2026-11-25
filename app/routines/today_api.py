"""Rutinas de hoy for the parents' Hoy (padres-barra.html): with the code. Before the
routines' /{routine_id} routes (main.py)."""

from fastapi import APIRouter, Depends

from app.clock import app_day
from app.deps import get_clock, get_config_store, require_parent
from app.missions.repository import WEEKDAYS
from app.routines.api import get_runs_repository
from app.routines.day_list import routines_of_day
from app.routines.repository import RoutinesRepository, RunsRepository
from app.settings import SettingsRepository
from app.storage.config_store import ConfigStore

router = APIRouter(prefix="/api/routines", tags=["routines"], dependencies=[Depends(require_parent)])


@router.get("/today")
def routines_today(
    store: ConfigStore = Depends(get_config_store),
    runs: RunsRepository = Depends(get_runs_repository),
    clock=Depends(get_clock),
) -> list[dict]:
    settings = SettingsRepository(store)
    if not settings.features().routines:
        return []
    now = clock.now()
    day = app_day(now, settings.settings().day_starts_at)
    routines = RoutinesRepository(store).list()
    finished = {r.id for r in routines if runs.get(day, r.id)["finished_at"]}
    return routines_of_day(routines, WEEKDAYS[day.weekday()], now.hour * 60 + now.minute, finished)
