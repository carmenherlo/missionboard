"""The parents' hand on the routine going on: finish it for today, or (started by hand)
pause it and let it go on (18/11), and who is in it (rutinas-flexibles.html). Always with the parents' code."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.children.api import public_child
from app.deps import require_parent
from app.routines.api import get_routines_service
from app.routines.service import RoutinesService

router = APIRouter(prefix="/api/routines", tags=["routines"], dependencies=[Depends(require_parent)])


class PausedIn(BaseModel):
    paused: bool


class WhoIn(BaseModel):
    kids: list[str]


@router.post("/{routine_id}/finish", status_code=204)
def finish(routine_id: str, routines: RoutinesService = Depends(get_routines_service)) -> None:
    routines.finish(routine_id)


@router.put("/{routine_id}/paused", status_code=204)
def pause(routine_id: str, body: PausedIn, routines: RoutinesService = Depends(get_routines_service)) -> None:
    routines.pause(routine_id, body.paused)


@router.get("/{routine_id}/who")
def who(routine_id: str, routines: RoutinesService = Depends(get_routines_service)) -> list[dict]:
    """¿Quién está? (rutinas-flexibles.html): its mission's children, and who is in it now."""
    children, here = routines.who(routine_id)
    return [{**public_child(c), "here": c.id in here} for c in children]


@router.put("/{routine_id}/who", status_code=204)
def set_who(routine_id: str, body: WhoIn, routines: RoutinesService = Depends(get_routines_service)) -> None:
    routines.set_who(routine_id, body.kids)
