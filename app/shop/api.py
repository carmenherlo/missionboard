from dataclasses import asdict
from datetime import date

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
from app.shop.orders import OrdersService
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


def build_orders(state, events: EventLog) -> OrdersService:
    """The orders, from the app's shared objects (the routes, and the phones' buttons)."""
    return OrdersService(state.purchases_repository, SettingsRepository(state.config_store), state.clock,
                         events, state.home_assistant)


def get_orders_service(request: Request, events: EventLog = Depends(get_event_log)) -> OrdersService:
    return build_orders(request.app.state, events)


def get_shop_service(
    orders: OrdersService = Depends(get_orders_service),
    store: ConfigStore = Depends(get_config_store),
    purchases: PurchasesRepository = Depends(get_purchases_repository),
    days: DayRepository = Depends(get_day_repository),
    libraries: ImageLibraries = Depends(get_image_libraries),
    photos: PhotoStore = Depends(get_photo_store),
    clock=Depends(get_clock),
    events: EventLog = Depends(get_event_log),
) -> ShopService:
    return ShopService(ShopRepository(store), purchases, days, ChildrenRepository(store), SettingsRepository(store),
                       libraries, photos, clock, events, orders)


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
            "orders": [self.order(o) for o in view["orders"]],
            **({"order_id": view["order_id"]} if "order_id" in view else {}),
        }

    def order(self, order: dict) -> dict:
        keep = ("id", "day", "child_id", "child_name", "item_text", "price", "at", "delivered_at", "due_day",
                "state", "nights", "progress")
        return {**{k: order[k] for k in keep}, "image_url": self._libraries.url(order["item_image"])}


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


@router.post("/children/{child_id}/orders/{order_id}/seen", status_code=204)
def order_seen(child_id: str, order_id: int, orders: OrdersService = Depends(get_orders_service)) -> None:
    """The child has seen it arrive (the box opened on their screen)."""
    orders.seen(child_id, order_id)


@router.get("/orders/summary")
def orders_summary(orders: OrdersService = Depends(get_orders_service)):
    """Per child: orders on their way and arrived not seen (the home and the route point at them)."""
    return orders.summary()


# ---------- Padres · Pedidos ----------


class DueIn(BaseModel):
    due_day: date | None = None


@router.get("/orders", dependencies=parent_only)
def list_orders(orders: OrdersService = Depends(get_orders_service), present: Presenter = Depends()):
    view = orders.for_parents()
    return {name: [present.order(o) for o in view[name]] for name in ("waiting", "handed")}


@router.patch("/orders/{order_id}", dependencies=parent_only)
def set_due(order_id: int, body: DueIn, orders: OrdersService = Depends(get_orders_service),
            present: Presenter = Depends()):
    order = orders.set_due(order_id, body.due_day)
    return present.order({**order, **orders.tracked(order)})


@router.post("/orders/{order_id}/deliver", dependencies=parent_only)
def deliver(order_id: int, orders: OrdersService = Depends(get_orders_service), present: Presenter = Depends()):
    order = orders.deliver(order_id)
    return present.order({**order, **orders.tracked(order)})


@router.get("/notify/phones", dependencies=parent_only)
def phones(orders: OrdersService = Depends(get_orders_service)):
    """Whether Home Assistant is there (only in the add-on), and its phones."""
    return orders.phones()
