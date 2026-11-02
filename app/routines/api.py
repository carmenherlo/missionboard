from typing import Literal

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, Field, field_validator

from app.children import avatars
from app.children.api import public_child
from app.children.repository import ChildrenRepository
from app.deps import get_clock, get_config_store, get_event_log, get_image_libraries, get_photo_store, require_parent
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.missions.repository import MissionsRepository
from app.routines.editor import RoutinesEditor
from app.routines.repository import TIME, Routine, RoutinesRepository, RunsRepository, hhmm
from app.routines.service import NOTES, Current, RoutinesService, kids_of
from app.storage.photo_store import PhotoStore
from app.settings import SettingsRepository
from app.storage.config_store import ConfigStore
from app.today.api import get_day_service
from app.today.service import DayService

router = APIRouter(prefix="/api/routines", tags=["routines"])
parent_only = [Depends(require_parent)]


def _not_blank(value):
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("Must not be empty")
    return value


class RoutineCreate(BaseModel):
    name: str = Field(max_length=40)
    wake: str = Field(pattern=TIME)

    _name = field_validator("name")(_not_blank)


class GoalIn(BaseModel):
    name: str = Field(max_length=60)
    at: str = Field(pattern=TIME)
    say: str = Field(default="¡A salir de casa!", max_length=200)

    _name = field_validator("name")(_not_blank)


class RoutinePatch(BaseModel):
    name: str | None = Field(default=None, max_length=40)
    days: list[str] | None = None
    wake: str | None = Field(default=None, pattern=TIME)
    remind_every: int | None = Field(default=None, ge=0, le=30)
    goal: GoalIn | None = None

    _name = field_validator("name")(_not_blank)


class KidsIn(BaseModel):
    kids: list[str]


class MissionIn(BaseModel):
    mission_id: str | None = None


class PartCreate(BaseModel):
    name: str = Field(max_length=60)

    _name = field_validator("name")(_not_blank)


class PartPatch(BaseModel):
    name: str | None = Field(default=None, max_length=60)
    image: str | None = None
    at: str | None = Field(default=None, pattern=TIME)
    minutes: int | None = Field(default=None, ge=1, le=180)
    say: str | None = Field(default=None, max_length=200)
    tasks: list[str] | None = None
    warnings: list[int] | None = None
    check_mission: bool | None = None

    _name = field_validator("name")(_not_blank)


class OrderIn(BaseModel):
    ids: list[str]


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


def get_routines_editor(
    store: ConfigStore = Depends(get_config_store),
    libraries: ImageLibraries = Depends(get_image_libraries),
    photos: PhotoStore = Depends(get_photo_store),
    events: EventLog = Depends(get_event_log),
) -> RoutinesEditor:
    return RoutinesEditor(
        RoutinesRepository(store), ChildrenRepository(store), MissionsRepository(store), libraries, photos, events
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


@router.post("/{routine_id}/finish", status_code=204, dependencies=parent_only)
def finish(routine_id: str, routines: RoutinesService = Depends(get_routines_service)) -> None:
    routines.finish(routine_id)


# ---------- Configurar → Rutinas ----------


class Editing:
    """A routine for its editor: as stored, with each part's times worked out,
    and the warnings worth showing (a child's mission closing before it ends)."""

    def __init__(
        self,
        libraries: ImageLibraries = Depends(get_image_libraries),
        store: ConfigStore = Depends(get_config_store),
    ):
        self._libraries = libraries
        self._children = ChildrenRepository(store)
        self._missions = MissionsRepository(store)

    def __call__(self, routine: Routine) -> dict:
        timeline = routine.timeline()
        kids = kids_of(routine, self._children.list())
        conflicts = []
        for child in kids:
            mission = self._missions.get(routine.missions.get(child.id) or "")
            if mission and mission.schedule and mission.schedule.end and mission.schedule.end < hhmm(routine.ends):
                conflicts.append({"child": child.name, "mission": mission.name, "mission_id": mission.id,
                                  "closes": mission.schedule.end, "ends": hhmm(routine.ends)})
        return {
            **routine.to_doc(),
            "every_child": not routine.kids,
            "kids": [c.id for c in kids],
            "ends": hhmm(routine.ends),
            "parts": [
                {**part.model_dump(mode="json"), "image_url": self._libraries.url(part.image),
                 "start": hhmm(start), "end": hhmm(end)}
                for part, start, end in timeline
            ],
            "conflicts": conflicts,
        }


@router.get("")
def list_routines(editor: RoutinesEditor = Depends(get_routines_editor), present: Editing = Depends()):
    return [present(r) for r in editor.list_all()]


@router.post("", status_code=201, dependencies=parent_only)
def create_routine(body: RoutineCreate, editor: RoutinesEditor = Depends(get_routines_editor),
                   present: Editing = Depends()):
    return present(editor.create(body.name, body.wake))


@router.get("/{routine_id}")
def get_routine(routine_id: str, editor: RoutinesEditor = Depends(get_routines_editor), present: Editing = Depends()):
    return present(editor.get(routine_id))


@router.patch("/{routine_id}", dependencies=parent_only)
def update_routine(routine_id: str, body: RoutinePatch, editor: RoutinesEditor = Depends(get_routines_editor),
                   present: Editing = Depends()):
    changes = {name: getattr(body, name) for name in body.model_fields_set}
    for required in ("name", "days", "wake", "remind_every"):
        if changes.get(required, "") is None:
            changes.pop(required)
    if changes.get("goal") is not None:
        changes["goal"] = changes["goal"].model_dump()
    return present(editor.update(routine_id, **changes))


@router.delete("/{routine_id}", status_code=204, dependencies=parent_only)
def delete_routine(routine_id: str, editor: RoutinesEditor = Depends(get_routines_editor)) -> None:
    editor.delete(routine_id)


@router.put("/{routine_id}/kids", dependencies=parent_only)
def set_kids(routine_id: str, body: KidsIn, editor: RoutinesEditor = Depends(get_routines_editor),
             present: Editing = Depends()):
    return present(editor.set_kids(routine_id, body.kids))


@router.put("/{routine_id}/missions/{child_id}", dependencies=parent_only)
def set_mission(routine_id: str, child_id: str, body: MissionIn,
                editor: RoutinesEditor = Depends(get_routines_editor), present: Editing = Depends()):
    return present(editor.set_mission(routine_id, child_id, body.mission_id))


@router.post("/{routine_id}/parts", status_code=201, dependencies=parent_only)
def add_part(routine_id: str, body: PartCreate, editor: RoutinesEditor = Depends(get_routines_editor),
             present: Editing = Depends()):
    return present(editor.add_part(routine_id, body.name))


@router.put("/{routine_id}/parts/order", dependencies=parent_only)
def reorder_parts(routine_id: str, body: OrderIn, editor: RoutinesEditor = Depends(get_routines_editor),
                  present: Editing = Depends()):
    return present(editor.reorder_parts(routine_id, body.ids))


@router.patch("/{routine_id}/parts/{part_id}", dependencies=parent_only)
def update_part(routine_id: str, part_id: str, body: PartPatch,
                editor: RoutinesEditor = Depends(get_routines_editor), present: Editing = Depends()):
    changes = {name: getattr(body, name) for name in body.model_fields_set}
    for required in ("name", "minutes", "tasks", "check_mission"):
        if changes.get(required, "") is None:
            changes.pop(required)
    return present(editor.update_part(routine_id, part_id, **changes))


@router.delete("/{routine_id}/parts/{part_id}", dependencies=parent_only)
def delete_part(routine_id: str, part_id: str, editor: RoutinesEditor = Depends(get_routines_editor),
                present: Editing = Depends()):
    return present(editor.delete_part(routine_id, part_id))


@router.put("/{routine_id}/parts/{part_id}/photo", dependencies=parent_only)
async def upload_part_photo(routine_id: str, part_id: str, request: Request, content_type: str = Header(),
                            editor: RoutinesEditor = Depends(get_routines_editor), present: Editing = Depends()):
    media_type = content_type.split(";")[0].strip().lower()
    return present(editor.set_part_photo(routine_id, part_id, await request.body(), media_type))


@router.get("/{routine_id}/trial", dependencies=parent_only)
def trial(
    routine_id: str,
    from_part: int = Query(default=0, alias="from", ge=0),
    editor: RoutinesEditor = Depends(get_routines_editor),
    routines: RoutinesService = Depends(get_routines_service),
    libraries: ImageLibraries = Depends(get_image_libraries),
    clock=Depends(get_clock),
):
    """"Probar ahora": the routine as if it were on now, for this device only."""
    now = clock.now()
    routine = editor.trial(routine_id, now, from_part)
    current = routines.current_for(routine, now)
    editor.tested(routine_id)
    return {**_present(current, libraries), "trial": True}
