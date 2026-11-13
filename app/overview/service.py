"""Padres · Hoy and Padres · Niño (step 7): how each child is doing today, what is
waiting to be handed over (orders and prizes of the wheel), and a child's stars
over the last days with their history."""

from datetime import timedelta
from types import SimpleNamespace

from app.children.repository import ChildrenRepository
from app.clock import Clock
from app.errors import NotFoundError
from app.missions.repository import child_tasks
from app.events.service import EventLog
from app.settings import SettingsRepository
from app.shop.orders import OrdersService
from app.today.repository import DayRepository
from app.today.service import DayService, Today

CHART_DAYS = 14  # Padres · Niño: stars won each day, these many days back
HISTORY = 30  # and their latest movements


class OverviewService:
    def __init__(self, days: DayService, records: DayRepository, orders: OrdersService, children: ChildrenRepository,
                 settings: SettingsRepository, clock: Clock, events: EventLog):
        self._days = days
        self._records = records
        self._orders = orders
        self._children = children
        self._settings = settings
        self._clock = clock
        self._events = events

    def today(self) -> dict:
        """Every child's day, the orders not handed over and the prizes not given."""
        return {
            "children": [self._days.today(child.id) for child in self._children.list()],
            "orders": self._orders.for_parents()["waiting"],
            "prizes": self._records.prizes_to_give(),
        }

    def setup(self, missions: list, code_is_default: bool, prizes: int, shop: int, routines: int) -> dict:
        """Primeros pasos: what is ready of the app (it goes away once the first four are)."""
        children = self._children.list()
        return {
            "children": len(children),
            "missions": len(missions),
            "switched_on": any(child_tasks(m, c.id) for m in missions for c in children),
            "code_changed": not code_is_default,
            "prizes": prizes,
            "shop": shop,
            "routines": routines,
        }

    def child(self, child_id: str) -> dict:
        today: Today = self._days.today(child_id)
        since = today.day - timedelta(days=CHART_DAYS - 1)
        earned = self._records.earned_by_day(child_id, since)
        return {
            "today": today,
            "chart": [{"day": (d := since + timedelta(days=n)).isoformat(), "stars": earned.get(d.isoformat(), 0)}
                      for n in range(CHART_DAYS)],
            "movements": self._records.movements(child_id, HISTORY),
        }

    def deliver_prize(self, spin_id: int) -> None:
        spin = self._records.prize_spin(spin_id)
        if spin is None:
            raise NotFoundError("Prize not found")
        if spin["delivered_at"] is None:
            self._records.deliver_prize(spin_id, self._clock.now())
            self._events.config_changed(
                "prize", "delivered", child=SimpleNamespace(id=spin["child_id"], name=spin["child_name"]),
                mission=SimpleNamespace(id=spin["prize_id"], name=spin["prize_text"]))
