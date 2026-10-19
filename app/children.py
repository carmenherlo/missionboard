import secrets
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from app import avatars, config_store
from app.parents import require_parent

router = APIRouter(prefix="/api", tags=["children"])

PHOTOS_DIRNAME = "photos"
MAX_PHOTO_BYTES = 5 * 1024 * 1024
PHOTO_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


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


def _data_dir(request: Request) -> Path:
    return request.app.state.data_dir


def _photos_dir(request: Request) -> Path:
    return _data_dir(request) / PHOTOS_DIRNAME


def _public(child: dict) -> dict:
    photo = child.get("photo")
    return {
        **child,
        "photo_url": f"/api/children/{child['id']}/photo?v={photo}" if photo else None,
    }


def _find(config: dict, child_id: str) -> dict:
    for child in config["children"]:
        if child["id"] == child_id:
            return child
    raise HTTPException(status_code=404, detail="Child not found")


def _resolve_avatar(body: ChildIn, config: dict, child_id: str | None) -> tuple[str | None, str]:
    """Validate the avatar choice and return (preset, color)."""
    if body.avatar_type == "preset":
        preset = avatars.PRESETS_BY_ID.get(body.preset or "")
        if preset is None:
            raise HTTPException(status_code=422, detail="Unknown preset")
        color = preset["color"]
    else:
        if body.color not in avatars.PALETTE_COLORS:
            raise HTTPException(status_code=422, detail="Color must come from the palette")
        preset, color = None, body.color

    if any(c["color"] == color and c["id"] != child_id for c in config["children"]):
        raise HTTPException(status_code=409, detail="Color already in use")
    return (preset["id"] if preset else None), color


def _remove_photo(request: Request, filename: str | None) -> None:
    if filename:
        (_photos_dir(request) / filename).unlink(missing_ok=True)


def _sniff_photo_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


@router.get("/avatars")
def list_avatars():
    return {"presets": avatars.PRESETS, "palette": avatars.PALETTE}


@router.get("/children")
def list_children(request: Request):
    config = config_store.load(_data_dir(request))
    return [_public(child) for child in config["children"]]


@router.post("/children", status_code=201, dependencies=[Depends(require_parent)])
def create_child(body: ChildIn, request: Request):
    with config_store.edit(_data_dir(request)) as config:
        preset, color = _resolve_avatar(body, config, child_id=None)
        child = {
            "id": secrets.token_hex(4),
            "name": body.name,
            "avatar_type": body.avatar_type,
            "preset": preset,
            "photo": None,
            "color": color,
        }
        config["children"].append(child)
    return _public(child)


@router.put("/children/{child_id}", dependencies=[Depends(require_parent)])
def update_child(child_id: str, body: ChildIn, request: Request):
    with config_store.edit(_data_dir(request)) as config:
        child = _find(config, child_id)
        preset, color = _resolve_avatar(body, config, child_id=child_id)
        old_photo = child["photo"]
        child.update(
            name=body.name,
            avatar_type=body.avatar_type,
            preset=preset,
            photo=old_photo if body.avatar_type == "photo" else None,
            color=color,
        )
    if child["photo"] is None:
        _remove_photo(request, old_photo)
    return _public(child)


@router.delete("/children/{child_id}", status_code=204, dependencies=[Depends(require_parent)])
def delete_child(child_id: str, request: Request) -> None:
    # Only the config entry and avatar go away; history in SQLite (when it exists) stays.
    with config_store.edit(_data_dir(request)) as config:
        child = _find(config, child_id)
        config["children"].remove(child)
    _remove_photo(request, child["photo"])


@router.put("/children/{child_id}/photo", dependencies=[Depends(require_parent)])
async def upload_photo(child_id: str, request: Request, content_type: str = Header()):
    """Upload the raw image as the request body (no multipart needed)."""
    media_type = content_type.split(";")[0].strip().lower()
    if media_type not in PHOTO_TYPES:
        raise HTTPException(status_code=415, detail="Photo must be JPEG, PNG or WebP")
    data = await request.body()
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Photo is too large (max 5 MB)")
    if _sniff_photo_type(data) != media_type:
        raise HTTPException(status_code=422, detail="File content does not match its type")

    photos_dir = _photos_dir(request)
    photos_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{child_id}-{secrets.token_hex(4)}{PHOTO_TYPES[media_type]}"

    with config_store.edit(_data_dir(request)) as config:
        child = _find(config, child_id)
        (photos_dir / filename).write_bytes(data)
        old_photo = child["photo"]
        child.update(avatar_type="photo", preset=None, photo=filename)
    _remove_photo(request, old_photo)
    return _public(child)


@router.get("/children/{child_id}/photo")
def get_photo(child_id: str, request: Request):
    child = _find(config_store.load(_data_dir(request)), child_id)
    if not child.get("photo"):
        raise HTTPException(status_code=404, detail="Child has no photo")
    path = _photos_dir(request) / child["photo"]
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Photo file missing")
    return FileResponse(path)
