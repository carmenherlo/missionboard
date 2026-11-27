"""A child's stars: how many they have, and the ones a parent gives or takes away
(Padres · Niño). The ones won with missions are in today/; the ones spent, in shop/."""

from app.children.repository import ChildrenRepository
from app.clock import Clock, app_day
from app.errors import InvalidError
from app.events.service import EventLog
from app.stars.repository import StarsRepository


class StarsService:
    def __init__(
        self,
        children: ChildrenRepository,
        stars: StarsRepository,
        clock: Clock,
        events: EventLog,
    ):
        self._children = children
        self._stars = stars
        self._clock = clock
        self._events = events

    def balance(self, child_id: str) -> int:
        return self._stars.balance(self._children.require(child_id).id)

    def give(self, child_id: str, stars: int) -> int:
        """A parent gives a child some stars, as a present; says how many they have now."""
        child = self._children.require(child_id)
        now = self._clock.now()
        self._stars.give(child, stars, app_day(now), now)
        self._events.config_changed("stars", "given", child=child, changes={"gift": stars})
        return self._stars.balance(child.id)

    def take(self, child_id: str, stars: int) -> int:
        """A parent takes some stars away (Padres · Niño); never more than they have."""
        child = self._children.require(child_id)
        if stars > self._stars.balance(child.id):
            raise InvalidError("Not that many stars")
        now = self._clock.now()
        self._stars.give(child, -stars, app_day(now), now, "taken")
        self._events.config_changed("stars", "taken", child=child, changes={"gift": -stars})
        return self._stars.balance(child.id)

    def movements(self, child_id: str, limit: int) -> list[dict]:
        return self._stars.movements(child_id, limit)

    def by_day(self, child_id: str, reason: str, since) -> dict[str, int]:
        return self._stars.by_day(child_id, reason, since)
