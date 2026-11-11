from dataclasses import asdict

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from app.avatars.repository import AvatarFiles, AvatarsRepository, FamilyAvatar
from app.avatars.service import AvatarsService
from app.children import avatars as app_avatars
from app.children.repository import ChildrenRepository
from app.deps import get_avatar_files, get_config_store, get_event_log, get_image_libraries, require_parent
from app.errors import InvalidError, NotFoundError
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.storage.config_store import ConfigStore

router = APIRouter(prefix="/api/avatars", tags=["avatars"])
parent_only = [Depends(require_parent)]

NAME_MAX = 30


def _not_blank(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Must not be empty")
    return value


class AvatarPatch(BaseModel):
    name: str | None = Field(default=None, max_length=NAME_MAX)
    color: str | None = None
    color_suggested: bool | None = None

    _name = field_validator("name")(lambda v: v if v is None else _not_blank(v))


def get_avatars_service(
    store: ConfigStore = Depends(get_config_store),
    files: AvatarFiles = Depends(get_avatar_files),
    events: EventLog = Depends(get_event_log),
) -> AvatarsService:
    return AvatarsService(AvatarsRepository(store), files, ChildrenRepository(store), events)


def picture_url(avatar: FamilyAvatar) -> str:
    # By its file: a new picture is a new address, so no tablet keeps showing the old one.
    return f"api/avatars/pictures/{avatar.image}"


def present(avatar: FamilyAvatar, avatars: AvatarsService) -> dict:
    return {**asdict(avatar), "label": avatar.name, "family": True, "image_url": picture_url(avatar),
            "worn_by": [c.name for c in avatars.worn_by(avatar.id)]}


@router.get("")
def list_avatars(avatars: AvatarsService = Depends(get_avatars_service),
                 libraries: ImageLibraries = Depends(get_image_libraries)):
    """The family's, the app's animals (with who wears each) and the palette."""
    presets = [{**preset, "image_url": libraries.url(preset["image"]),
                "worn_by": [c.name for c in avatars.worn_by(preset["id"])]} for preset in app_avatars.PRESETS]
    return {"family": [present(a, avatars) for a in avatars.list()], "presets": presets,
            "palette": app_avatars.PALETTE, "mission_colors": app_avatars.MISSION_COLORS}


@router.post("", status_code=201, dependencies=parent_only)
async def upload_avatar(
    request: Request,
    name: str = Query(max_length=NAME_MAX),
    color: str = Query(),
    suggested: bool = Query(False),
    avatars: AvatarsService = Depends(get_avatars_service),
):
    """The picture as the body (like the photos: no form), its name and colour in the address."""
    if not name.strip():
        raise InvalidError("Must not be empty")
    return present(avatars.upload(await request.body(), name.strip(), color, suggested), avatars)


@router.get("/{avatar_id}")
def get_avatar(avatar_id: str, avatars: AvatarsService = Depends(get_avatars_service)):
    return present(avatars.get(avatar_id), avatars)


@router.patch("/{avatar_id}", dependencies=parent_only)
def update_avatar(avatar_id: str, body: AvatarPatch, avatars: AvatarsService = Depends(get_avatars_service)):
    return present(avatars.update(avatar_id, name=body.name, color=body.color, suggested=body.color_suggested), avatars)


@router.put("/{avatar_id}/picture", dependencies=parent_only)
async def change_picture(
    avatar_id: str,
    request: Request,
    color: str | None = Query(None),  # the one the browser suggests from the new picture
    avatars: AvatarsService = Depends(get_avatars_service),
):
    return present(avatars.set_picture(avatar_id, await request.body(), color), avatars)


@router.delete("/{avatar_id}", status_code=204, dependencies=parent_only)
def delete_avatar(avatar_id: str, avatars: AvatarsService = Depends(get_avatars_service)) -> None:
    avatars.delete(avatar_id)


@router.get("/pictures/{filename}")
def avatar_picture(filename: str, files: AvatarFiles = Depends(get_avatar_files)):
    path = files.path(filename) if "/" not in filename and not filename.startswith(".") else None
    if path is None:
        raise NotFoundError("Avatar picture not found")
    return FileResponse(path)
