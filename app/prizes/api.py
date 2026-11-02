from dataclasses import asdict

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field, field_validator

from app.deps import get_config_store, get_event_log, get_image_libraries, get_photo_store, require_parent
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.prizes.repository import Prize, PrizesRepository
from app.prizes.service import PrizesService
from app.storage.config_store import ConfigStore
from app.storage.photo_store import PhotoStore

router = APIRouter(prefix="/api/prizes", tags=["prizes"])
parent_only = [Depends(require_parent)]

PRIZE_TEXT_MAX = 40


def _not_blank(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("Must not be empty")
    return value


class PrizeCreate(BaseModel):
    text: str = Field(max_length=PRIZE_TEXT_MAX)

    _text = field_validator("text")(_not_blank)


class PrizePatch(BaseModel):
    text: str | None = Field(default=None, max_length=PRIZE_TEXT_MAX)
    image: str | None = None

    _text = field_validator("text")(_not_blank)


def get_prizes_service(
    store: ConfigStore = Depends(get_config_store),
    libraries: ImageLibraries = Depends(get_image_libraries),
    photos: PhotoStore = Depends(get_photo_store),
    events: EventLog = Depends(get_event_log),
) -> PrizesService:
    return PrizesService(PrizesRepository(store), libraries, photos, events)


class Presenter:
    def __init__(self, libraries: ImageLibraries = Depends(get_image_libraries)):
        self._libraries = libraries

    def __call__(self, prize: Prize) -> dict:
        return {**asdict(prize), "image_url": self._libraries.url(prize.image)}


@router.get("")
def list_prizes(prizes: PrizesService = Depends(get_prizes_service), present: Presenter = Depends()):
    return [present(p) for p in prizes.list()]


@router.post("", status_code=201, dependencies=parent_only)
def create_prize(
    body: PrizeCreate, prizes: PrizesService = Depends(get_prizes_service), present: Presenter = Depends()
):
    return present(prizes.create(body.text))


@router.get("/{prize_id}")
def get_prize(prize_id: str, prizes: PrizesService = Depends(get_prizes_service), present: Presenter = Depends()):
    return present(prizes.get(prize_id))


@router.patch("/{prize_id}", dependencies=parent_only)
def update_prize(
    prize_id: str,
    body: PrizePatch,
    prizes: PrizesService = Depends(get_prizes_service),
    present: Presenter = Depends(),
):
    changes = {name: getattr(body, name) for name in body.model_fields_set}
    if changes.get("text", "") is None:
        changes.pop("text")
    return present(prizes.update(prize_id, **changes))


@router.put("/{prize_id}/photo", dependencies=parent_only)
async def upload_prize_photo(
    prize_id: str,
    request: Request,
    content_type: str = Header(),
    prizes: PrizesService = Depends(get_prizes_service),
    present: Presenter = Depends(),
):
    """Upload the raw image as the request body (no multipart needed)."""
    media_type = content_type.split(";")[0].strip().lower()
    return present(prizes.set_photo(prize_id, await request.body(), media_type))


@router.delete("/{prize_id}", status_code=204, dependencies=parent_only)
def delete_prize(prize_id: str, prizes: PrizesService = Depends(get_prizes_service)) -> None:
    prizes.delete(prize_id)
