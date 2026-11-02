from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.children import avatars
from app.children.api import public_child
from app.children.repository import ChildrenRepository
from app.deps import get_clock, get_config_store, get_event_log, get_image_libraries, require_parent
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.routines.repository import RoutinesRepository, RunsRepository, hhmm
from app.routines.service import NOTES, Current, RoutinesService
from app.settings import SettingsRepository
from app.storage.config_store import ConfigStore
from app.today.api import get_day_service
from app.today.service import DayService

router = APIRouter(prefix="/api/routines", tags=["routines"])


class NoteIn(BaseModel):
    kind: Literal[NOTES]
    part: int | None = Field(default=None, ge=0)
    seconds: int | None = Field(default=None, ge=0)
    early: bool = False
    phase: str | None = Field(default=None, pattern=r"^[\w-]{1,30}$")


def get_runs_repository(request: Request) -> RunsRepository:
    return request.app.state.runs_repository


def get_routines_service(
    store: ConfigStore = Depends(get_config_store),
    runs: RunsRepository = Depends(get_runs_repository),
    days: DayService = Depends(get_day_service),
    clock=Depends(get_clock),
    events: EventLog = Depends(get_event_log),
) -> RoutinesService:
    return RoutinesService(
        RoutinesRepository(store), runs, ChildrenRepository(store), days, SettingsRepository(store), clock, events
    )


def _present(current: Current, libraries: ImageLibraries) -> dict:
    routine = current.routine
    return {
        "id": routine.id,
        "name": routine.name,
        "day": current.day.isoformat(),
        "now": current.minute,  # minute of the day by the household's clock, with seconds
        "wake": routine.wake,
        "remind_every": routine.remind_every,
        "parts": [
            {
                "name": part.name,
                "image_url": libraries.url(part.image),
                "say": part.say,
                "tasks": list(part.tasks),
                "warnings": current.warnings(part),
                "check_mission": part.check_mission,
                "start": hhmm(start),
                "end": hhmm(end),
            }
            for part, start, end in routine.timeline()
        ],
        "goal": routine.goal and {
            "name": routine.goal.name, "image_url": libraries.url(routine.goal.image),
            "at": routine.goal.at, "say": routine.goal.say,
        },
        "ends": hhmm(routine.ends),
        "stopped": bool(current.run["stopped_at"]),
        "closed_phase": current.run["closed_phase"],
        "people": [
            {"child": public_child(p.child), "colors": avatars.tones(p.child.color), "mission": p.mission}
            for p in current.people
        ],
    }


@router.get("/current")
def current_routine(
    routines: RoutinesService = Depends(get_routines_service),
    libraries: ImageLibraries = Depends(get_image_libraries),
):
    """The routine going on now (null if none): the screen asks every little while."""
    current = routines.current()
    return _present(current, libraries) if current else None


# The routine's screen is for everyone in the house: no parent code, except to finish it.
@router.post("/{routine_id}/notes", status_code=204)
def note(routine_id: str, body: NoteIn, routines: RoutinesService = Depends(get_routines_service)) -> None:
    routines.note(routine_id, body.kind, part=body.part, seconds=body.seconds, early=body.early, phase=body.phase)


@router.post("/{routine_id}/finish", status_code=204, dependencies=[Depends(require_parent)])
def finish(routine_id: str, routines: RoutinesService = Depends(get_routines_service)) -> None:
    routines.finish(routine_id)
