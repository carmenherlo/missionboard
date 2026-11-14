"""The daily prize at the end of a child's route (paso-5.html): locked until every
mission of today is done (a closed one means no prize today), then unlocked for
settings.daily_prize_spins spins, then won (showing what it was). The day (today/)
asks for it; spinning the wheel is in service.py."""

from dataclasses import dataclass
from datetime import date

from app.children.repository import Child
from app.daily_prize.repository import PrizeSpinsRepository
from app.prizes.repository import Prize, PrizesRepository
from app.settings import SettingsRepository

LOCKED, UNLOCKED, WON = "locked", "unlocked", "won"


@dataclass
class PrizeToday:
    state: str
    prizes: list[Prize]  # the wheel
    won: list[dict]  # what came out today: {"prize_id", "text", "image"}
    spins_left: int


class PrizeBoard:
    def __init__(self, prizes: PrizesRepository, spins: PrizeSpinsRepository, settings: SettingsRepository):
        self._prizes = prizes
        self._spins = spins
        self._settings = settings

    def today(self, day: date, child: Child, missions: int, all_done: bool) -> PrizeToday | None:
        """None: no prize at the end of the route (switched off, no prizes, no missions today)."""
        spins = self._settings.settings().daily_prize_spins
        prizes = self._prizes.list()
        if not self._settings.features().daily_prize or not prizes or not missions or spins == 0:
            return None
        won = self._spins.won(day, child.id)
        spins_left = max(0, spins - len(won))
        if not all_done:
            state = LOCKED
        else:
            state = UNLOCKED if spins_left else WON
        return PrizeToday(state=state, prizes=prizes, won=won, spins_left=spins_left)
