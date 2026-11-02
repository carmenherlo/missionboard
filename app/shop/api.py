from dataclasses import asdict

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field, field_validator

from app.children import avatars
from app.children.api import public_child
from app.children.repository import ChildrenRepository
from app.deps import get_clock, get_config_store, get_event_log, get_image_libraries, get_photo_store, require_parent
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.settings import SettingsRepository
from app.shop.repository import PurchasesRepository, ShopItem, ShopRepository
from app.shop.service import ShopService
from app.storage.config_store import ConfigStore
from app.storage.photo_store import PhotoStore
from app.today.api import get_day_repository
from app.today.repository import DayRepository

router = APIRouter(prefix="/api", tags=["shop"])
parent_only = [Depends(require_parent)]

ITEM_TEXT_MAX = 40
PRICE = Field(ge=1, le=999)


def _not_blank(value):
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("Must not be empty")
    return value


class ItemCreate(BaseModel):
    text: str = Field(max_length=ITEM_TEXT_MAX)
    price: int = PRICE

    _text = field_validator("text")(_not_blank)


class ItemPatch(BaseModel):
    text: str | None = Field(default=None, max_length=ITEM_TEXT_MAX)
    image: str | None = None
    price: int | None = Field(default=None, ge=1, le=999)

    _text = field_validator("text")(_not_blank)


def get_purchases_repository(request: Request) -> PurchasesRepository:
    return request.app.state.purchases_repository


def get_shop_service(
    store: ConfigStore = Depends(get_config_store),
    purchases: PurchasesRepository = Depends(get_purchases_repository),
    days: DayRepository = Depends(get_day_repository),
    libraries: ImageLibraries = Depends(get_image_libraries),
    photos: PhotoStore = Depends(get_photo_store),
    clock=Depends(get_clock),
    events: EventLog = Depends(get_event_log),
) -> ShopService:
    return ShopService(ShopRepository(store), purchases, days, ChildrenRepository(store), SettingsRepository(store),
                       libraries, photos, clock, events)


class Presenter:
    def __init__(self, libraries: ImageLibraries = Depends(get_image_libraries)):
        self._libraries = libraries

    def item(self, item: ShopItem) -> dict:
        return {**asdict(item), "image_url": self._libraries.url(item.image)}

    def child(self, view: dict) -> dict:
        return {
            "child": public_child(view["child"]),
            "colors": avatars.tones(view["child"].color),
            "stars": view["stars"],
            "star_url": self._libraries.url("fluent/star"),
            "items": [{**self.item(i), "affordable": i.price <= view["stars"]} for i in view["items"]],
            "purchases": [{**p, "image_url": self._libraries.url(p["item_image"])} for p in view["purchases"]],
        }


# ---------- Configurar → Tienda ----------


@router.get("/shop")
def list_items(shop: ShopService = Depends(get_shop_service), present: Presenter = Depends()):
    return [present.item(i) for i in shop.list()]


@router.post("/shop", status_code=201, dependencies=parent_only)
def create_item(body: ItemCreate, shop: ShopService = Depends(get_shop_service), present: Presenter = Depends()):
    return present.item(shop.create(body.text, body.price))


@router.get("/shop/{item_id}")
def get_item(item_id: str, shop: ShopService = Depends(get_shop_service), present: Presenter = Depends()):
    return present.item(shop.get(item_id))


@router.patch("/shop/{item_id}", dependencies=parent_only)
def update_item(item_id: str, body: ItemPatch, shop: ShopService = Depends(get_shop_service),
                present: Presenter = Depends()):
    changes = {name: getattr(body, name) for name in body.model_fields_set}
    for required in ("text", "price"):
        if changes.get(required, "") is None:
            changes.pop(required)
    return present.item(shop.update(item_id, **changes))


@router.put("/shop/{item_id}/photo", dependencies=parent_only)
async def upload_item_photo(item_id: str, request: Request, content_type: str = Header(),
                            shop: ShopService = Depends(get_shop_service), present: Presenter = Depends()):
    media_type = content_type.split(";")[0].strip().lower()
    return present.item(shop.set_photo(item_id, await request.body(), media_type))


@router.delete("/shop/{item_id}", status_code=204, dependencies=parent_only)
def delete_item(item_id: str, shop: ShopService = Depends(get_shop_service)) -> None:
    shop.delete(item_id)


# ---------- Mis estrellas (the child's side: no code) ----------


@router.get("/children/{child_id}/shop")
def child_shop(child_id: str, shop: ShopService = Depends(get_shop_service), present: Presenter = Depends()):
    return present.child(shop.for_child(child_id))


@router.post("/children/{child_id}/shop/{item_id}/buy")
def buy(child_id: str, item_id: str, shop: ShopService = Depends(get_shop_service), present: Presenter = Depends()):
    """Buy it with the child's stars (422 if they do not have enough)."""
    return present.child(shop.buy(child_id, item_id))
