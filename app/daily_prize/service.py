"""Spinning the wheel of the daily prize, and the parents handing it over (Pendiente de dar)."""

import secrets

from dataclasses import dataclass
from types import SimpleNamespace

from app.clock import Clock
from app.daily_prize.repository import PrizeSpinsRepository
from app.daily_prize.state import UNLOCKED
from app.errors import ConflictError, NotFoundError
from app.events.service import EventLog
from app.prizes.repository import Prize
from app.today.service import DayService, Today


@dataclass
class SpinResult:
    today: Today
    prize: Prize


class DailyPrizeService:
    def __init__(self, days: DayService, spins: PrizeSpinsRepository, clock: Clock, events: EventLog,
                 choose=secrets.choice):  # tests can pass their own, to know the prize
        self._days = days
        self._spins = spins
        self._clock = clock
        self._events = events
        self._choose = choose

    def spin(self, child_id: str) -> SpinResult:
        """Spin the wheel: the prize is chosen and kept here; the screen only shows it."""
        today = self._days.today(child_id)
        if today.prize is None or today.prize.state != UNLOCKED:
            raise ConflictError("The prize is not unlocked")
        prize = self._choose(today.prize.prizes)
        self._spins.add(today.day, today.child, prize, self._clock.now())
        self._events.child_did("prize_spun", today.child, prize=prize.text)
        return SpinResult(self._days.today(child_id), prize)

    def to_give(self) -> list[dict]:
        return self._spins.to_give()

    def deliver(self, spin_id: int) -> None:
        spin = self._spins.get(spin_id)
        if spin is None:
            raise NotFoundError("Prize not found")
        if spin["delivered_at"] is None:
            self._spins.deliver(spin_id, self._clock.now())
            self._events.config_changed(
                "prize", "delivered", child=SimpleNamespace(id=spin["child_id"], name=spin["child_name"]),
                mission=SimpleNamespace(id=spin["prize_id"], name=spin["prize_text"]))
