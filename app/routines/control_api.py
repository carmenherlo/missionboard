"""The parents' hand on the routine going on: finish it for today, or (started by hand)
pause it and let it go on (18/11). Always with the parents' code."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.deps import require_parent
from app.routines.api import get_routines_service
from app.routines.service import RoutinesService

router = APIRouter(prefix="/api/routines", tags=["routines"], dependencies=[Depends(require_parent)])


class PausedIn(BaseModel):
    paused: bool


@router.post("/{routine_id}/finish", status_code=204)
def finish(routine_id: str, routines: RoutinesService = Depends(get_routines_service)) -> None:
    routines.finish(routine_id)


@router.put("/{routine_id}/paused", status_code=204)
def pause(routine_id: str, body: PausedIn, routines: RoutinesService = Depends(get_routines_service)) -> None:
    routines.pause(routine_id, body.paused)
