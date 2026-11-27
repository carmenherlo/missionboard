"""Who a mission is for, and which tasks each child does (misiones-para-quien.html)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.children.repository import ChildrenRepository
from app.deps import get_config_store, get_event_log, require_parent
from app.events.service import EventLog
from app.missions.api import Presenter
from app.missions.kids import MissionKidsService
from app.missions.repository import MissionsRepository
from app.routines.repository import RoutinesRepository
from app.storage.config_store import ConfigStore

router = APIRouter(prefix="/api", tags=["missions"], dependencies=[Depends(require_parent)])


class OnIn(BaseModel):
    on: bool


class ActiveIn(BaseModel):
    active: bool


def get_mission_kids_service(
    store: ConfigStore = Depends(get_config_store), events: EventLog = Depends(get_event_log)
) -> MissionKidsService:
    return MissionKidsService(MissionsRepository(store), ChildrenRepository(store), RoutinesRepository(store), events)


@router.put("/missions/{mission_id}/children/{child_id}")
def set_kid(
    mission_id: str,
    child_id: str,
    body: OnIn,
    kids: MissionKidsService = Depends(get_mission_kids_service),
    present: Presenter = Depends(),
):
    """Put a child in the mission or take them out."""
    return present(kids.set_kid(mission_id, child_id, body.on))


@router.put("/missions/{mission_id}/children/{child_id}/tasks/{task_id}")
def set_task(
    mission_id: str,
    child_id: str,
    task_id: str,
    body: ActiveIn,
    kids: MissionKidsService = Depends(get_mission_kids_service),
    present: Presenter = Depends(),
):
    """Switch a task, with its steps, on or off for one child."""
    return present(kids.set_task(mission_id, child_id, task_id, body.active))
