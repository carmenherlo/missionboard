from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from app.children import avatars
from app.children.repository import Child, ChildrenRepository
from app.children.service import ChildData, ChildrenService
from app.deps import get_config_store, get_event_log, get_image_libraries, get_photo_store, require_parent
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.missions.api import get_missions_service
from app.missions.service import MissionsService
from app.storage.config_store import ConfigStore
from app.storage.photo_store import PhotoStore

router = APIRouter(prefix="/api", tags=["children"])


class ChildIn(BaseModel):
    name: str = Field(max_length=30)
    avatar_type: Literal["preset", "photo"]
    preset: str | None = None
    color: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be empty")
        return value


def get_children_service(
    store: ConfigStore = Depends(get_config_store),
    photos: PhotoStore = Depends(get_photo_store),
    missions: MissionsService = Depends(get_missions_service),
    events: EventLog = Depends(get_event_log),
) -> ChildrenService:
    return ChildrenService(ChildrenRepository(store), photos, events, dependents=[missions])


def public_child(child: Child) -> dict:
    """A child as the screens get it: with the address of their photo."""
    return {
        **asdict(child),
        "photo_url": f"/api/children/{child.id}/photo?v={child.photo}" if child.photo else None,
    }


@router.get("/avatars")
def list_avatars(libraries: ImageLibraries = Depends(get_image_libraries)):
    presets = [{**preset, "image_url": libraries.url(preset["image"])} for preset in avatars.PRESETS]
    return {"presets": presets, "palette": avatars.PALETTE, "picker_columns": avatars.PICKER_COLUMNS}


@router.get("/children")
def list_children(children: ChildrenService = Depends(get_children_service)):
    return [public_child(child) for child in children.list()]


@router.post("/children", status_code=201, dependencies=[Depends(require_parent)])
def create_child(body: ChildIn, children: ChildrenService = Depends(get_children_service)):
    return public_child(children.create(ChildData(**body.model_dump())))


@router.put("/children/{child_id}", dependencies=[Depends(require_parent)])
def update_child(
    child_id: str, body: ChildIn, children: ChildrenService = Depends(get_children_service)
):
    return public_child(children.update(child_id, ChildData(**body.model_dump())))


@router.delete("/children/{child_id}", status_code=204, dependencies=[Depends(require_parent)])
def delete_child(child_id: str, children: ChildrenService = Depends(get_children_service)) -> None:
    children.delete(child_id)


@router.put("/children/{child_id}/photo", dependencies=[Depends(require_parent)])
async def upload_photo(
    child_id: str,
    request: Request,
    content_type: str = Header(),
    children: ChildrenService = Depends(get_children_service),
):
    """Upload the raw image as the request body (no multipart needed)."""
    media_type = content_type.split(";")[0].strip().lower()
    return public_child(children.set_photo(child_id, await request.body(), media_type))


@router.get("/children/{child_id}/photo")
def get_photo(child_id: str, children: ChildrenService = Depends(get_children_service)):
    return FileResponse(children.photo_path(child_id))
