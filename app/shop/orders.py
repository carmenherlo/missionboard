"""What was bought, as an order on its way (tienda-2.html, concept A).

An order goes from the shop to home: "on_way" until a parent hands it over, then
"arrived" until the child has seen it arrive on their screen, then "done". A parent
may say when it arrives (due_day); the child sees how many nights are left and the
truck moving along the road. The parents' phones hear of each order, with buttons
(Home Assistant), and are reminded on the day it was due.
"""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

from app.clock import Clock, app_day
from app.errors import NotFoundError
from app.events.service import EventLog
from app.notify import HomeAssistant
from app.settings import SettingsRepository
from app.shop.repository import PurchasesRepository

DONE_SHOWN = 5  # "Mis pedidos": the latest received, under those on their way
HANDED_SHOWN = 10  # Padres · Pedidos: the latest handed over

# The truck on the road (0: at the shop, 1: home). Never at either end while on its way.
START, ALMOST = 0.1, 0.85
NO_DATE = 0.15

ACTION = "MISSIONBOARD_ORDER"  # MISSIONBOARD_ORDER_<id>_<TODAY|TOMORROW|GIVEN>


def track(order: dict, today: date) -> dict:
    """Where an order is: its state, the nights left and the truck on the road."""
    if order["seen_at"]:
        return {"state": "done", "nights": None, "progress": 1.0}
    if order["delivered_at"]:
        return {"state": "arrived", "nights": None, "progress": 1.0}
    if not order["due_day"]:
        return {"state": "on_way", "nights": None, "progress": NO_DATE}
    due = date.fromisoformat(order["due_day"])
    nights = max((due - today).days, 0)
    total = (due - date.fromisoformat(order["day"])).days
    if nights == 0:
        progress = ALMOST
    else:
        progress = START + (ALMOST - START) * max(0.0, 1 - nights / total) if total > 0 else START
    return {"state": "on_way", "nights": nights, "progress": round(progress, 3)}


class OrdersService:
    def __init__(self, purchases: PurchasesRepository, settings: SettingsRepository, clock: Clock,
                 events: EventLog, home_assistant: HomeAssistant):
        self._purchases = purchases
        self._settings = settings
        self._clock = clock
        self._events = events
        self._ha = home_assistant

    # ---------- the child's side ----------

    def of_child(self, child_id: str) -> list[dict]:
        today = self._today()
        return [{**order, **track(order, today)} for order in self._purchases.of_child(child_id, DONE_SHOWN)]

    def summary(self) -> dict[str, dict]:
        """Per child: orders on their way and arrived but not seen (the truck and the box)."""
        counts: dict[str, dict] = {}
        for order in self._purchases.not_seen():
            kind = "arrived" if order["delivered_at"] else "on_way"
            counts.setdefault(order["child_id"], {"on_way": 0, "arrived": 0})[kind] += 1
        return counts

    def seen(self, child_id: str, order_id: int) -> None:
        """The child has seen it arrive: from now on, one of their things."""
        order = self._get(order_id)
        if order["child_id"] != child_id:
            raise NotFoundError("Order not found")
        if order["delivered_at"] and not order["seen_at"]:
            self._purchases.set(order_id, seen_at=self._stamp())
            self._events.child_did("order_seen", _child(order), mission=_item(order))

    # ---------- the parents' side ----------

    def for_parents(self) -> dict:
        today = self._today()
        return {
            "waiting": [{**o, **track(o, today)} for o in self._purchases.waiting()],
            "handed": [{**o, **track(o, today)} for o in self._purchases.handed_over(HANDED_SHOWN)],
        }

    def set_due(self, order_id: int, due: date | None) -> dict:
        order = self._get(order_id)
        if not order["delivered_at"]:
            value = due.isoformat() if due else None
            if value != order["due_day"]:
                # A new day: reminded again on it.
                self._purchases.set(order_id, due_day=value, reminded_day=None)
                self._events.config_changed("order", "due", child=_child(order), mission=_item(order),
                                            changes={"due_day": due})
        return self._get(order_id)

    def deliver(self, order_id: int) -> dict:
        order = self._get(order_id)
        if not order["delivered_at"]:
            self._purchases.set(order_id, delivered_at=self._stamp())
            self._events.config_changed("order", "delivered", child=_child(order), mission=_item(order))
        return self._get(order_id)

    def tracked(self, order: dict) -> dict:
        return track(order, self._today())

    # ---------- the phones ----------

    def ordered(self, order_id: int) -> None:
        """Just bought: tell the parents' phones, with buttons to say when it arrives."""
        order = self._get(order_id)
        stars = order["price"]
        self._send(order, f"🛒 {order['child_name']} ha pedido «{order['item_text']}»",
                   f"Pagó {stars} {'estrella' if stars == 1 else 'estrellas'}. ¿Cuándo le llega?",
                   [("TODAY", "Hoy"), ("TOMORROW", "Mañana"), ("GIVEN", "Ya se lo di")])

    def remind(self) -> None:
        """Orders due today (or before) and not handed over: once a day, from remind_at."""
        now = self._clock.now()
        settings = self._settings.settings()
        if now.strftime("%H:%M") < settings.shop_notify.remind_at:
            return
        today = self._today()
        for order in self._purchases.waiting():
            due = order["due_day"]
            if not due or date.fromisoformat(due) > today or order["reminded_day"] == today.isoformat():
                continue
            self._purchases.set(order["id"], reminded_day=today.isoformat())
            self._send(order, f"🚚 Hoy llega «{order['item_text']}» de {order['child_name']}",
                       "¿Ya se lo has dado?", [("GIVEN", "Ya se lo di"), ("TOMORROW", "Mañana")])

    def on_action(self, action: str) -> bool:
        """A button tapped on a phone ("MISSIONBOARD_ORDER_12_TODAY"); false if it is not ours."""
        prefix, _, rest = action.rpartition("_ORDER_")
        number, _, what = rest.partition("_")
        if prefix != ACTION.removesuffix("_ORDER") or not number.isdigit():
            return False
        order_id, today = int(number), self._today()
        try:
            if what == "TODAY":
                self.set_due(order_id, today)
            elif what == "TOMORROW":
                self.set_due(order_id, today + timedelta(days=1))
            elif what == "GIVEN":
                self.deliver(order_id)
            else:
                return False
        except NotFoundError:
            return False
        return True

    def phones(self) -> dict:
        """For Configurar → Tienda: whether there is Home Assistant, and its phones."""
        if not self._ha.available:
            return {"available": False, "phones": []}
        try:
            return {"available": True, "phones": self._ha.phones()}
        except Exception:  # noqa: BLE001 - Home Assistant not answering
            return {"available": True, "phones": [], "error": True}

    def _send(self, order: dict, title: str, message: str, buttons: list[tuple[str, str]]) -> None:
        phones = list(self._settings.settings().shop_notify.phones)
        actions = [(f"{ACTION}_{order['id']}_{code}", text) for code, text in buttons]
        self._ha.send(phones, title, message, actions, tag=f"missionboard-order-{order['id']}")

    # ----------

    def _get(self, order_id: int) -> dict:
        order = self._purchases.get(order_id)
        if order is None:
            raise NotFoundError("Order not found")
        return order

    def _today(self) -> date:
        return app_day(self._clock.now(), self._settings.settings().day_starts_at)

    def _stamp(self) -> str:
        now: datetime = self._clock.now()
        return now.isoformat(timespec="seconds")


def _child(order: dict):
    return SimpleNamespace(id=order["child_id"], name=order["child_name"])


def _item(order: dict):
    return SimpleNamespace(id=order["item_id"], name=order["item_text"])
