"""Padres · Hoy and Padres · Niño (step 7): how each child is doing today, what is
waiting to be handed over (orders and prizes of the wheel), and a child's stars
over the last days with their history."""

from datetime import timedelta

from app.children.repository import ChildrenRepository
from app.daily_prize.service import DailyPrizeService
from app.missions.repository import child_tasks
from app.shop.orders import OrdersService
from app.stars.service import StarsService
from app.streaks.service import StreaksService
from app.today.service import DayService, Today

CHART_DAYS = 14  # Padres · Niño: stars won each day, these many days back
HISTORY = 30  # and their latest movements


class OverviewService:
    def __init__(
        self,
        days: DayService,
        stars: StarsService,
        prizes: DailyPrizeService,
        streaks: StreaksService,
        orders: OrdersService,
        children: ChildrenRepository,
    ):
        self._days = days
        self._stars = stars
        self._prizes = prizes
        self._streaks = streaks
        self._orders = orders
        self._children = children

    def today(self) -> dict:
        """Every child's day, the orders not handed over and the prizes not given."""
        children = self._children.list()
        weeks = {child.id: self._streaks.week(child.id) for child in children}  # settles the weeks just closed
        return {
            "children": [self._days.today(child.id) for child in children],
            "weeks": weeks,
            "orders": self._orders.for_parents()["waiting"],
            "prizes": self._prizes.to_give(),
            "week_prizes": self._streaks.prizes_to_give(),
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
        earned = self._stars.earned_by_day(child_id, since)
        return {
            "today": today,
            "week": self._streaks.week(child_id),
            "chart": [
                {"day": (d := since + timedelta(days=n)).isoformat(), "stars": earned.get(d.isoformat(), 0)}
                for n in range(CHART_DAYS)
            ],
            "movements": self._stars.movements(child_id, HISTORY),
        }
