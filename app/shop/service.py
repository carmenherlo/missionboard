from __future__ import annotations

import secrets
from dataclasses import replace
from types import SimpleNamespace

from app.children.repository import ChildrenRepository
from app.clock import Clock, app_day
from app.errors import ConflictError, InvalidError, NotFoundError
from app.events.service import EventLog
from app.images.libraries import ImageLibraries, photo_filename, photo_ref
from app.images.photos import validate_photo
from app.images.rules import ImageRules
from app.settings import SettingsRepository
from app.shop.orders import OrdersService
from app.shop.repository import PurchasesRepository, ShopItem, ShopRepository
from app.storage.photo_store import PhotoStore
from app.today.repository import DayRepository

UNSET = object()


class ShopService:
    """The shop (step 6): its items, edited like the daily prizes with a price;
    and buying one with a child's stars."""

    def __init__(
        self,
        items: ShopRepository,
        purchases: PurchasesRepository,
        days: DayRepository,
        children: ChildrenRepository,
        settings: SettingsRepository,
        libraries: ImageLibraries,
        photos: PhotoStore,
        clock: Clock,
        events: EventLog,
        orders: OrdersService,
    ):
        self._orders = orders
        self._items = items
        self._purchases = purchases
        self._days = days
        self._children = children
        self._settings = settings
        self._photos = photos
        self._images = ImageRules(libraries, photos)
        self._clock = clock
        self._events = events

    # ---------- the items (Configurar → Tienda) ----------

    def list(self) -> list[ShopItem]:
        return self._items.list()

    def get(self, item_id: str) -> ShopItem:
        item = self._items.get(item_id)
        if item is None:
            raise NotFoundError("Item not found")
        return item

    def create(self, text: str, price: int) -> ShopItem:
        image, suggested = self._images.suggest(text)
        item = ShopItem(id=secrets.token_hex(4), text=text, price=price, image=image, image_suggested=suggested)
        self._items.add(item)
        self._log("created", item)
        return item

    def update(self, item_id: str, *, text=UNSET, image=UNSET, price=UNSET, hidden_from=UNSET) -> ShopItem:
        with self._items.atomic():
            old = self.get(item_id)
            item = replace(old)
            if text is not UNSET:
                item.text = text
            if price is not UNSET:
                item.price = price
            if hidden_from is not UNSET:
                known = {c.id for c in self._children.list()}
                if not set(hidden_from) <= known:
                    raise NotFoundError("Child not found")
                item.hidden_from = sorted(set(hidden_from))
            if image is not UNSET:
                item.image = self._images.check_new_image(old.image, image)
                item.image_suggested = False
            self._items.update(item)
        self._images.drop_replaced_photo(old.image, item.image)
        changes = {("name" if f == "text" else f): getattr(item, f) for f in ("text", "image", "price")
                   if getattr(item, f) != getattr(old, f)}
        if item.hidden_from != old.hidden_from:
            changes["shop_for"] = [c.name for c in self._children.list() if item.for_child(c.id)]
        if changes:
            self._log("changed", item, changes)
        return item

    def reorder(self, item_ids: list[str]) -> list[ShopItem]:
        with self._items.atomic():
            current = [i.id for i in self._items.list()]
            if sorted(current) != sorted(item_ids):
                raise InvalidError("The order must list every item exactly once")
            self._items.reorder(item_ids)
        items = self._items.list()
        if item_ids != current:
            self._events.config_changed("shop_item", "reordered", changes={"order": [i.text for i in items]})
        return items

    def set_photo(self, item_id: str, data: bytes, media_type: str) -> ShopItem:
        extension = validate_photo(data, media_type)
        with self._items.atomic():
            old = self.get(item_id)
            filename = self._photos.save(data, prefix=item_id, extension=extension)
            item = replace(old, image=photo_ref(filename), image_suggested=False)
            self._items.update(item)
        self._images.drop_replaced_photo(old.image, item.image)
        self._log("changed", item, {"image": item.image})
        return item

    def delete(self, item_id: str) -> None:
        with self._items.atomic():
            item = self.get(item_id)
            self._items.remove(item_id)
        self._photos.delete(photo_filename(item.image))
        self._log("deleted", item)

    # ---------- the child's side ----------

    def for_child(self, child_id: str) -> dict:
        """Their stars, what they can buy, and their orders (on their way, arrived, received)."""
        child = self._child(child_id)
        return {
            "child": child,
            "stars": self._days.stars(child.id),
            "items": [i for i in self._items.list() if i.for_child(child.id)] if self._settings.features().shop else [],
            "orders": self._orders.of_child(child.id),
        }

    def buy(self, child_id: str, item_id: str) -> dict:
        if not self._settings.features().shop:
            raise ConflictError("The shop is off")
        child = self._child(child_id)
        item = self.get(item_id)
        if not item.for_child(child.id):
            raise NotFoundError("Item not found")
        now = self._clock.now()
        day = app_day(now, self._settings.settings().day_starts_at)
        order_id = self._purchases.buy(day, child, item, now)
        if order_id is None:
            raise InvalidError("Not enough stars")
        self._events.child_did("purchase", child, mission=SimpleNamespace(id=item.id, name=item.text),
                               stars=-item.price)
        self._orders.ordered(order_id)
        return {**self.for_child(child_id), "order_id": order_id}

    def _child(self, child_id: str):
        child = self._children.get(child_id)
        if child is None:
            raise NotFoundError("Child not found")
        return child

    def _log(self, action: str, item: ShopItem, changes: dict | None = None) -> None:
        named = SimpleNamespace(id=item.id, name=item.text)
        self._events.config_changed("shop_item", action, mission=named, changes=changes)
