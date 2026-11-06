from dataclasses import asdict

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field, field_validator

from app.children import avatars
from app.children.repository import ChildrenRepository
from app.deps import get_config_store, get_event_log, get_image_libraries, get_photo_store, require_parent
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.missions.repository import Mission, MissionsRepository, Schedule
from app.missions.service import MissionsService
from app.routines import links
from app.routines.repository import RoutinesRepository, hhmm
from app.storage.config_store import ConfigStore
from app.storage.photo_store import PhotoStore

router = APIRouter(prefix="/api", tags=["missions"])
parent_only = [Depends(require_parent)]

MISSION_NAME_MAX = 40
TASK_TEXT_MAX = 60
STEP_TEXT_MAX = 60


def _not_blank(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Must not be empty")
    return value


def _not_blank_or_none(value: str | None) -> str | None:
    return value if value is None else _not_blank(value)


class ScheduleIn(BaseModel):
    start: str
    end: str | None = None


class MissionCreate(BaseModel):
    name: str = Field(max_length=MISSION_NAME_MAX)
    image: str | None = None

    _name = field_validator("name")(_not_blank)


class MissionPatch(BaseModel):
    """Only the fields sent are changed (the editor saves each change on its own)."""

    name: str | None = Field(default=None, max_length=MISSION_NAME_MAX)
    image: str | None = None
    days: list[str] | None = None
    schedule: ScheduleIn | None = None
    color: str | None = None

    _name = field_validator("name")(_not_blank_or_none)


class TaskCreate(BaseModel):
    text: str = Field(max_length=TASK_TEXT_MAX)

    _text = field_validator("text")(_not_blank)


class TaskPatch(BaseModel):
    text: str | None = Field(default=None, max_length=TASK_TEXT_MAX)
    image: str | None = None
    days: list[str] | None = None  # null: the mission's days

    _text = field_validator("text")(_not_blank_or_none)


class StepCreate(BaseModel):
    text: str = Field(max_length=STEP_TEXT_MAX)

    _text = field_validator("text")(_not_blank)


class StepPatch(BaseModel):
    text: str | None = Field(default=None, max_length=STEP_TEXT_MAX)
    image: str | None = None

    _text = field_validator("text")(_not_blank_or_none)


class StepPlace(BaseModel):
    task_id: str
    position: int = Field(ge=0)


class OrderIn(BaseModel):
    ids: list[str]


class ActiveIn(BaseModel):
    active: bool


def get_missions_service(
    store: ConfigStore = Depends(get_config_store),
    libraries: ImageLibraries = Depends(get_image_libraries),
    photos: PhotoStore = Depends(get_photo_store),
    events: EventLog = Depends(get_event_log),
) -> MissionsService:
    return MissionsService(MissionsRepository(store), ChildrenRepository(store), libraries, photos, events,
                           RoutinesRepository(store))


def _changes(body: BaseModel, required: set[str] = frozenset()) -> dict:
    """Fields actually sent. Null is only meaningful where it can mean "remove"."""
    changes = {name: getattr(body, name) for name in body.model_fields_set}
    for name in required & changes.keys():
        if changes[name] is None:
            changes.pop(name)
    return changes


def _media_type(content_type: str) -> str:
    return content_type.split(";")[0].strip().lower()


class Presenter:
    """Turns missions into JSON: the URL of every image, the tones of its colour, how
    much each child has switched on, and its routine."""

    def __init__(self, libraries: ImageLibraries = Depends(get_image_libraries),
                 store: ConfigStore = Depends(get_config_store)):
        self._libraries = libraries
        self._store = store
        self._cache = None

    def _context(self):
        if self._cache is None:
            self._cache = (ChildrenRepository(self._store).list(),
                           links.routine_by_mission(RoutinesRepository(self._store).list()))
        return self._cache

    def __call__(self, mission: Mission) -> dict:
        children, routines = self._context()
        data = asdict(mission)
        data["image_url"] = self._libraries.url(mission.image)
        data["colors"] = avatars.tones(mission.color)
        for task in data["tasks"]:
            task["image_url"] = self._libraries.url(task["image"])
            for step in task["steps"]:
                step["image_url"] = self._libraries.url(step["image"])
        total = len(mission.items())
        data["children"] = [
            {"id": c.id, "active": sum(mission.is_on(c.id, i.id) for i in mission.items()), "total": total}
            for c in children
        ]
        routine = routines.get(mission.id)
        data["routine"] = routine and {
            "id": routine.id, "days": list(routine.days), "manual": routine.manual, "anchor": routine.anchor,
            "kids": [c.id for c in links.kids_of(routine, children)], "every_child": not routine.kids,
            "start": None if routine.manual else hhmm(routine.starts),
            "end": None if routine.manual else hhmm(routine.timeline()[-1][2]),  # when its parts end
            "goal": None if routine.manual else hhmm(routine.ends),
        }
        return data


@router.get("/missions")
def list_missions(missions: MissionsService = Depends(get_missions_service), present: Presenter = Depends()):
    return [present(m) for m in missions.list()]


@router.post("/missions", status_code=201, dependencies=parent_only)
def create_mission(body: MissionCreate, missions: MissionsService = Depends(get_missions_service),
                   present: Presenter = Depends()):
    return present(missions.create(body.name, body.image))


@router.put("/missions/order", dependencies=parent_only)
def reorder_missions(body: OrderIn, missions: MissionsService = Depends(get_missions_service),
                     present: Presenter = Depends()):
    return [present(m) for m in missions.reorder(body.ids)]


@router.get("/missions/{mission_id}")
def get_mission(mission_id: str, missions: MissionsService = Depends(get_missions_service),
                present: Presenter = Depends()):
    return present(missions.get(mission_id))


@router.patch("/missions/{mission_id}", dependencies=parent_only)
def update_mission(mission_id: str, body: MissionPatch, missions: MissionsService = Depends(get_missions_service),
                   present: Presenter = Depends()):
    changes = _changes(body, required={"name", "days", "color"})
    if changes.get("schedule") is not None:
        changes["schedule"] = Schedule(**changes["schedule"].model_dump())
    return present(missions.update(mission_id, **changes))


@router.delete("/missions/{mission_id}", status_code=204, dependencies=parent_only)
def delete_mission(mission_id: str, missions: MissionsService = Depends(get_missions_service)) -> None:
    missions.delete(mission_id)


@router.put("/missions/{mission_id}/photo", dependencies=parent_only)
async def upload_mission_photo(mission_id: str, request: Request, content_type: str = Header(),
                               missions: MissionsService = Depends(get_missions_service),
                               present: Presenter = Depends()):
    """Upload the raw image as the request body (no multipart needed)."""
    return present(missions.set_photo(mission_id, await request.body(), _media_type(content_type)))


# ---------- tasks ----------


@router.post("/missions/{mission_id}/tasks", status_code=201, dependencies=parent_only)
def add_task(mission_id: str, body: TaskCreate, missions: MissionsService = Depends(get_missions_service),
             present: Presenter = Depends()):
    return present(missions.add_task(mission_id, body.text))


@router.put("/missions/{mission_id}/tasks/order", dependencies=parent_only)
def reorder_tasks(mission_id: str, body: OrderIn, missions: MissionsService = Depends(get_missions_service),
                  present: Presenter = Depends()):
    return present(missions.reorder_tasks(mission_id, body.ids))


@router.patch("/missions/{mission_id}/tasks/{task_id}", dependencies=parent_only)
def update_task(mission_id: str, task_id: str, body: TaskPatch,
                missions: MissionsService = Depends(get_missions_service), present: Presenter = Depends()):
    return present(missions.update_task(mission_id, task_id, **_changes(body, required={"text"})))


@router.delete("/missions/{mission_id}/tasks/{task_id}", dependencies=parent_only)
def delete_task(mission_id: str, task_id: str, missions: MissionsService = Depends(get_missions_service),
                present: Presenter = Depends()):
    return present(missions.delete_task(mission_id, task_id))


@router.put("/missions/{mission_id}/tasks/{task_id}/photo", dependencies=parent_only)
async def upload_task_photo(mission_id: str, task_id: str, request: Request, content_type: str = Header(),
                            missions: MissionsService = Depends(get_missions_service),
                            present: Presenter = Depends()):
    return present(missions.set_task_photo(mission_id, task_id, await request.body(), _media_type(content_type)))


# ---------- steps ----------


@router.post("/missions/{mission_id}/tasks/{task_id}/steps", status_code=201, dependencies=parent_only)
def add_step(mission_id: str, task_id: str, body: StepCreate,
             missions: MissionsService = Depends(get_missions_service), present: Presenter = Depends()):
    return present(missions.add_step(mission_id, task_id, body.text))


@router.patch("/missions/{mission_id}/steps/{step_id}", dependencies=parent_only)
def update_step(mission_id: str, step_id: str, body: StepPatch,
                missions: MissionsService = Depends(get_missions_service), present: Presenter = Depends()):
    return present(missions.update_step(mission_id, step_id, **_changes(body, required={"text"})))


@router.delete("/missions/{mission_id}/steps/{step_id}", dependencies=parent_only)
def delete_step(mission_id: str, step_id: str, missions: MissionsService = Depends(get_missions_service),
                present: Presenter = Depends()):
    return present(missions.delete_step(mission_id, step_id))


@router.put("/missions/{mission_id}/steps/{step_id}/place", dependencies=parent_only)
def place_step(mission_id: str, step_id: str, body: StepPlace,
               missions: MissionsService = Depends(get_missions_service), present: Presenter = Depends()):
    """Order a step within its task, or drag it to another one."""
    return present(missions.place_step(mission_id, step_id, body.task_id, body.position))


@router.put("/missions/{mission_id}/steps/{step_id}/photo", dependencies=parent_only)
async def upload_step_photo(mission_id: str, step_id: str, request: Request, content_type: str = Header(),
                            missions: MissionsService = Depends(get_missions_service),
                            present: Presenter = Depends()):
    return present(missions.set_step_photo(mission_id, step_id, await request.body(), _media_type(content_type)))


# ---------- each child ----------


@router.put("/missions/{mission_id}/children/{child_id}/items/{item_id}", dependencies=parent_only)
def set_active(mission_id: str, child_id: str, item_id: str, body: ActiveIn,
               missions: MissionsService = Depends(get_missions_service), present: Presenter = Depends()):
    """Switch a task or a step on or off for one child."""
    return present(missions.set_active(mission_id, child_id, item_id, body.active))
