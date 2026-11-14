from fastapi import APIRouter, Depends

from app.daily_prize.repository import PrizeSpinsRepository
from app.daily_prize.service import DailyPrizeService
from app.deps import get_clock, get_event_log, get_prize_spins_repository
from app.events.service import EventLog
from app.today.api import Presenter, get_day_service
from app.today.service import DayService

# The children's zone: no parent code. Handing it over is in overview/ (with the code).
router = APIRouter(prefix="/api", tags=["daily_prize"])


def get_daily_prize_service(
    days: DayService = Depends(get_day_service),
    spins: PrizeSpinsRepository = Depends(get_prize_spins_repository),
    clock=Depends(get_clock),
    events: EventLog = Depends(get_event_log),
) -> DailyPrizeService:
    return DailyPrizeService(days, spins, clock, events)


@router.post("/children/{child_id}/today/prize/spin")
def spin(child_id: str, prizes: DailyPrizeService = Depends(get_daily_prize_service), present: Presenter = Depends()):
    """Spin the wheel: says which prize came out; the screen turns the wheel to it."""
    result = prizes.spin(child_id)
    return {"prize_id": result.prize.id, "today": present(result.today)}
