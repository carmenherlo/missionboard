from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.children.repository import ChildrenRepository
from app.day_marks.repository import DaySnapshotsRepository
from app.day_marks.service import DayMarksService
from app.day_off.repository import DayOffsRepository
from app.deps import (
    get_clock,
    get_config_store,
    get_day_offs_repository,
    get_day_repository,
    get_day_snapshots_repository,
    get_event_log,
    get_image_libraries,
    require_parent,
)
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.missions.repository import MissionsRepository
from app.settings import SettingsRepository
from app.storage.config_store import ConfigStore
from app.streaks.api import get_streaks_service
from app.streaks.service import StreaksService
from app.today.repository import DayRepository
from app.undo.api import get_undo_service
from app.undo.service import UndoService

# Padres · Niños: the week, mission by mission (semana-misiones.html). With the code.
router = APIRouter(prefix="/api/children/{child_id}/marks", tags=["day_marks"], dependencies=[Depends(require_parent)])


class StateIn(BaseModel):
    state: str  # done · missed · free · pending · active (which ones depend on the day)


def get_day_marks(
    undo: UndoService = Depends(get_undo_service),
    store: ConfigStore = Depends(get_config_store),
    days: DayRepository = Depends(get_day_repository),
    offs: DayOffsRepository = Depends(get_day_offs_repository),
    snapshots: DaySnapshotsRepository = Depends(get_day_snapshots_repository),
    streaks: StreaksService = Depends(get_streaks_service),
    clock=Depends(get_clock),
    events: EventLog = Depends(get_event_log),
) -> DayMarksService:
    return DayMarksService(
        undo,
        ChildrenRepository(store),
        MissionsRepository(store),
        days,
        offs,
        snapshots,
        streaks,
        SettingsRepository(store),
        clock,
        events,
    )


def _present(view: dict, libraries: ImageLibraries) -> dict:
    return {
        **{k: v for k, v in view.items() if k not in ("day", "missions")},
        "day": view["day"].isoformat(),
        "missions": [
            {
                "id": m["mission"].id,
                "name": m["mission"].name,
                "image_url": libraries.url(m["mission"].image),
                "state": m["state"],
            }
            for m in view["missions"]
        ],
    }


@router.get("")
def week(child_id: str, marks: DayMarksService = Depends(get_day_marks)) -> dict:
    """The days of the racha's week shown, as tabs; {"on": False} while rachas are off."""
    days = marks.week(child_id)
    if days is None:
        return {"on": False}
    return {"on": True, "days": [{"day": d["day"].isoformat(), "state": d["state"]} for d in days]}


@router.get("/{day}")
def day_marks(
    child_id: str,
    day: date,
    marks: DayMarksService = Depends(get_day_marks),
    libraries: ImageLibraries = Depends(get_image_libraries),
) -> dict:
    return _present(marks.day(child_id, day), libraries)


@router.put("/{day}/{mission_id}")
def set_state(
    child_id: str,
    day: date,
    mission_id: str,
    body: StateIn,
    marks: DayMarksService = Depends(get_day_marks),
    libraries: ImageLibraries = Depends(get_image_libraries),
) -> dict:
    """A tap on a mission: what it was that day."""
    return _present(marks.set_state(child_id, day, mission_id, body.state), libraries)


@router.post("/{day}/reset")
def reset(
    child_id: str,
    day: date,
    marks: DayMarksService = Depends(get_day_marks),
    libraries: ImageLibraries = Depends(get_image_libraries),
) -> dict:
    """«Deshacer cambios»: the day as the app had left it."""
    return _present(marks.reset(child_id, day), libraries)
