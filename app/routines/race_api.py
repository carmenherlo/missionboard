"""Modo carrera (modo-carrera.html): its settings in the editor, how a race ends and the
parent who checks it, and «± Tiempo» on any routine started by hand."""

from types import SimpleNamespace

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.children.repository import ChildrenRepository
from app.deps import (
    get_clock,
    get_config_store,
    get_event_log,
    get_races_repository,
    get_stars_repository,
    require_parent,
)
from app.errors import ConflictError
from app.events.service import EventLog
from app.routines.api import Editing, get_routines_editor, get_routines_service, get_runs_repository
from app.routines.editor import RoutinesEditor
from app.routines.extra_time import ExtraTime
from app.routines.model import Routine
from app.routines.race import RaceService
from app.routines.race_rules import Race
from app.routines.races_repository import RacesRepository
from app.routines.repository import RoutinesRepository, RunsRepository
from app.routines.service import RoutinesService
from app.stars.repository import StarsRepository
from app.storage.config_store import ConfigStore

router = APIRouter(prefix="/api/routines", tags=["routines"])
parent_only = [Depends(require_parent)]


class RaceIn(BaseModel):
    on_time: int = Field(default=1, ge=0, le=10)
    fast: int = Field(default=2, ge=0, le=10)
    review: bool = True


class SlowIn(BaseModel):
    minutes: int | None = Field(default=None, ge=1, le=180)  # null: it is a race too


class ReviewIn(BaseModel):
    give: bool


class ExtraIn(BaseModel):
    part_id: str
    minutes: int = Field(ge=-60, le=60)  # added (negative: taken)


def get_race_service(
    routines: RoutinesService = Depends(get_routines_service),
    store: ConfigStore = Depends(get_config_store),
    races: RacesRepository = Depends(get_races_repository),
    stars: StarsRepository = Depends(get_stars_repository),
    clock=Depends(get_clock),
    events: EventLog = Depends(get_event_log),
) -> RaceService:
    return RaceService(routines, races, stars, ChildrenRepository(store), clock, events)


# ---------- Configurar → Rutinas: "Con el reloj" or "Carrera" ----------


@router.put("/{routine_id}/race", dependencies=parent_only)
def set_race(
    routine_id: str,
    body: RaceIn | None = None,
    editor: RoutinesEditor = Depends(get_routines_editor),
    store: ConfigStore = Depends(get_config_store),
    events: EventLog = Depends(get_event_log),
    present: Editing = Depends(),
):
    """A race (with its extra stars) or, null, by the clock again. Only started by hand."""
    routine = editor.get(routine_id)
    if not routine.manual:
        raise ConflictError("Only a routine started by hand can be a race")
    race = body and Race(**body.model_dump())
    changed = Routine.model_validate({**routine.to_doc(), "race": race and race.model_dump()})
    RoutinesRepository(store).update(changed)
    events.config_changed("routine", "changed", mission=SimpleNamespace(id=routine.id, name=routine.name))
    return present(editor.get(routine_id))


@router.put("/{routine_id}/parts/{part_id}/slow", dependencies=parent_only)
def set_slow(
    routine_id: str,
    part_id: str,
    body: SlowIn,
    editor: RoutinesEditor = Depends(get_routines_editor),
    present: Editing = Depends(),
):
    """ "Sin prisa": its "¡Hecho!" only after these minutes; null, a race like the others."""
    return present(editor.update_part(routine_id, part_id, slow_minutes=body.minutes))


# ---------- The race going on ----------


@router.post("/{routine_id}/race/end")
def end_race(routine_id: str, races: RaceService = Depends(get_race_service)):
    """Everyone has done their tasks (no code: it is the kids' screen). Its result."""
    return races.end(routine_id)


@router.get("/races/to-review", dependencies=parent_only)
def races_to_review(races: RaceService = Depends(get_race_service)):
    """Today's races whose extra stars wait for a parent (Padres · Por dar)."""
    return races.to_review()


@router.post("/races/{race_id}/review", dependencies=parent_only)
def review_race(race_id: int, body: ReviewIn, races: RaceService = Depends(get_race_service)):
    return races.review(race_id, body.give)


@router.post("/{routine_id}/extra", dependencies=parent_only)
def add_extra(
    routine_id: str,
    body: ExtraIn,
    routines: RoutinesService = Depends(get_routines_service),
    runs: RunsRepository = Depends(get_runs_repository),
    events: EventLog = Depends(get_event_log),
):
    """«± Tiempo»: minutes added to (or taken from) a part, only today. How many it has now."""
    return {"minutes": ExtraTime(routines, runs, events).add(routine_id, body.part_id, body.minutes)}
