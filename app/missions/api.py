from dataclasses import asdict

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field, field_validator

from app.children.repository import ChildrenRepository
from app.deps import get_config_store, get_image_libraries, get_photo_store, require_parent
from app.images.libraries import ImageLibraries
from app.missions.repository import Mission, MissionsRepository, Schedule
from app.missions.service import MissionsService
from app.storage.config_store import ConfigStore
from app.storage.photo_store import PhotoStore

router = APIRouter(prefix="/api", tags=["missions"])
parent_only = [Depends(require_parent)]

MISSION_NAME_MAX = 40
STEP_TEXT_MAX = 60


def _not_blank(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Must not be empty")
    return value


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

    _name = field_validator("name")(lambda v: v if v is None else _not_blank(v))


class StepCreate(BaseModel):
    text: str = Field(max_length=STEP_TEXT_MAX)

    _text = field_validator("text")(_not_blank)


class StepPatch(BaseModel):
    text: str | None = Field(default=None, max_length=STEP_TEXT_MAX)
    image: str | None = None

    _text = field_validator("text")(lambda v: v if v is None else _not_blank(v))


class OrderIn(BaseModel):
    ids: list[str]


def get_missions_service(
    store: ConfigStore = Depends(get_config_store),
    libraries: ImageLibraries = Depends(get_image_libraries),
    photos: PhotoStore = Depends(get_photo_store),
) -> MissionsService:
    return MissionsService(MissionsRepository(store), ChildrenRepository(store), libraries, photos)


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
    """Turns missions into JSON, adding the URL of every image."""

    def __init__(self, libraries: ImageLibraries = Depends(get_image_libraries)):
        self._libraries = libraries

    def __call__(self, mission: Mission) -> dict:
        data = asdict(mission)
        data["image_url"] = self._libraries.url(mission.image)
        for step in data["steps"]:
            step["image_url"] = self._libraries.url(step["image"])
        return data


@router.get("/children/{child_id}/missions")
def list_missions(
    child_id: str,
    missions: MissionsService = Depends(get_missions_service),
    present: Presenter = Depends(),
):
    return [present(m) for m in missions.list_for_child(child_id)]


@router.post("/children/{child_id}/missions", status_code=201, dependencies=parent_only)
def create_mission(
    child_id: str,
    body: MissionCreate,
    missions: MissionsService = Depends(get_missions_service),
    present: Presenter = Depends(),
):
    return present(missions.create(child_id, body.name, body.image))


@router.put("/children/{child_id}/missions/order", dependencies=parent_only)
def reorder_missions(
    child_id: str,
    body: OrderIn,
    missions: MissionsService = Depends(get_missions_service),
    present: Presenter = Depends(),
):
    return [present(m) for m in missions.reorder(child_id, body.ids)]


@router.get("/missions/{mission_id}")
def get_mission(
    mission_id: str,
    missions: MissionsService = Depends(get_missions_service),
    present: Presenter = Depends(),
):
    return present(missions.get(mission_id))


@router.patch("/missions/{mission_id}", dependencies=parent_only)
def update_mission(
    mission_id: str,
    body: MissionPatch,
    missions: MissionsService = Depends(get_missions_service),
    present: Presenter = Depends(),
):
    changes = _changes(body, required={"name", "days"})
    if "schedule" in changes and changes["schedule"] is not None:
        changes["schedule"] = Schedule(**changes["schedule"].model_dump())
    return present(missions.update(mission_id, **changes))


@router.delete("/missions/{mission_id}", status_code=204, dependencies=parent_only)
def delete_mission(mission_id: str, missions: MissionsService = Depends(get_missions_service)) -> None:
    missions.delete(mission_id)


@router.put("/missions/{mission_id}/photo", dependencies=parent_only)
async def upload_mission_photo(
    mission_id: str,
    request: Request,
    content_type: str = Header(),
    missions: MissionsService = Depends(get_missions_service),
    present: Presenter = Depends(),
):
    """Upload the raw image as the request body (no multipart needed)."""
    data = await request.body()
    return present(missions.set_photo(mission_id, data, _media_type(content_type)))


@router.post("/missions/{mission_id}/steps", status_code=201, dependencies=parent_only)
def add_step(
    mission_id: str,
    body: StepCreate,
    missions: MissionsService = Depends(get_missions_service),
    present: Presenter = Depends(),
):
    return present(missions.add_step(mission_id, body.text))


@router.put("/missions/{mission_id}/steps/order", dependencies=parent_only)
def reorder_steps(
    mission_id: str,
    body: OrderIn,
    missions: MissionsService = Depends(get_missions_service),
    present: Presenter = Depends(),
):
    return present(missions.reorder_steps(mission_id, body.ids))


@router.patch("/missions/{mission_id}/steps/{step_id}", dependencies=parent_only)
def update_step(
    mission_id: str,
    step_id: str,
    body: StepPatch,
    missions: MissionsService = Depends(get_missions_service),
    present: Presenter = Depends(),
):
    return present(missions.update_step(mission_id, step_id, **_changes(body, required={"text"})))


@router.delete("/missions/{mission_id}/steps/{step_id}", dependencies=parent_only)
def delete_step(
    mission_id: str,
    step_id: str,
    missions: MissionsService = Depends(get_missions_service),
    present: Presenter = Depends(),
):
    return present(missions.delete_step(mission_id, step_id))


@router.put("/missions/{mission_id}/steps/{step_id}/photo", dependencies=parent_only)
async def upload_step_photo(
    mission_id: str,
    step_id: str,
    request: Request,
    content_type: str = Header(),
    missions: MissionsService = Depends(get_missions_service),
    present: Presenter = Depends(),
):
    data = await request.body()
    return present(missions.set_step_photo(mission_id, step_id, data, _media_type(content_type)))
