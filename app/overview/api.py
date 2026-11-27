"""Padres · Hoy and Padres · Niño (step 7), with the parents' code."""

from fastapi import APIRouter, Depends

from app.children import avatars
from app.children.api import public_child
from app.children.repository import ChildrenRepository
from app.daily_prize.api import get_daily_prize_service
from app.daily_prize.service import DailyPrizeService
from app.deps import get_config_store, get_image_libraries, require_parent
from app.images.libraries import ImageLibraries
from app.missions.repository import MissionsRepository
from app.overview.service import OverviewService
from app.parents.repository import DEFAULT_PARENT_CODE, ParentsRepository
from app.prizes.repository import PrizesRepository
from app.routines.race import RaceService
from app.routines.race_api import get_race_service
from app.routines.repository import RoutinesRepository
from app.shop.api import Presenter as ShopPresenter
from app.shop.api import get_orders_service
from app.shop.orders import OrdersService
from app.shop.repository import ShopRepository
from app.stars.api import get_stars_service
from app.stars.service import StarsService
from app.storage.config_store import ConfigStore
from app.streaks.api import get_streaks_service, present_week
from app.streaks.service import StreaksService
from app.today.api import Presenter as DayPresenter
from app.today.api import get_day_service
from app.today.service import DayService, Today

router = APIRouter(prefix="/api/overview", tags=["overview"], dependencies=[Depends(require_parent)])


def get_overview_service(
    days: DayService = Depends(get_day_service),
    stars: StarsService = Depends(get_stars_service),
    prizes: DailyPrizeService = Depends(get_daily_prize_service),
    streaks: StreaksService = Depends(get_streaks_service),
    orders: OrdersService = Depends(get_orders_service),
    store: ConfigStore = Depends(get_config_store),
) -> OverviewService:
    return OverviewService(days, stars, prizes, streaks, orders, ChildrenRepository(store))


class Presenter:
    def __init__(
        self,
        libraries: ImageLibraries = Depends(get_image_libraries),
        day: DayPresenter = Depends(),
        shop: ShopPresenter = Depends(),
    ):
        self._libraries = libraries
        self._day = day
        self._shop = shop

    def child_day(self, today: Today) -> dict:
        """The child's day as their own screen gets it, without what only the route needs."""
        full = self._day(today)
        return {
            "child": public_child(today.child),
            "colors": avatars.tones(today.child.color),
            "day": today.day.isoformat(),
            "stars": today.stars,
            "streak": today.streak,
            "day_off": today.day_off,  # the whole day let off (dias-libres.html)
            "missions": [
                {k: m[k] for k in ("id", "name", "image_url", "state", "schedule", "done", "total")}
                for m in full["missions"]
            ],
            "prize": full["prize"] and {"state": full["prize"]["state"], "won": full["prize"]["won"]},
        }

    def order(self, order: dict) -> dict:
        return self._shop.order(order)

    def prize(self, spin: dict) -> dict:
        return {**spin, "image_url": self._libraries.url(spin["prize_image"])}


@router.get("/today")
def overview_today(overview: OverviewService = Depends(get_overview_service), present: Presenter = Depends()):
    view = overview.today()
    return {
        "children": [
            {**present.child_day(today), "week": present_week(view["weeks"][today.child.id])}
            for today in view["children"]
        ],
        "orders": [present.order(o) for o in view["orders"]],
        "prizes": [present.prize(p) for p in view["prizes"]],
        "week_prizes": [
            {k: p[k] for k in ("child_id", "child_name", "week_end", "tier", "prize_text")} for p in view["week_prizes"]
        ],
    }


@router.get("/to-give")
def to_give(overview: OverviewService = Depends(get_overview_service), races: RaceService = Depends(get_race_service)):
    """The number on «Por dar» in the parents' menu: what to hand over and the races to check."""
    return {"count": overview.to_give() + len(races.to_review())}


@router.get("/setup")
def setup(overview: OverviewService = Depends(get_overview_service), store: ConfigStore = Depends(get_config_store)):
    """Primeros pasos (Zona de padres): children, missions, switched on for someone, the code changed."""
    return overview.setup(
        MissionsRepository(store).list(),
        ParentsRepository(store).code() == DEFAULT_PARENT_CODE,
        len(PrizesRepository(store).list()),
        len(ShopRepository(store).list()),
        len(RoutinesRepository(store).live()),
    )


@router.get("/children/{child_id}")
def overview_child(
    child_id: str, overview: OverviewService = Depends(get_overview_service), present: Presenter = Depends()
):
    view = overview.child(child_id)
    return {
        **present.child_day(view["today"]),
        "week": present_week(view["week"]),
        "chart": view["chart"],
        "movements": view["movements"],
    }


@router.get("/children/{child_id}/movements")
def child_movements(child_id: str, overview: OverviewService = Depends(get_overview_service)):
    """A child's stars in and out, all of them (the card shows only the latest)."""
    return overview.movements(child_id)


@router.post("/prizes/{spin_id}/deliver", status_code=204)
def deliver_prize(spin_id: int, prizes: DailyPrizeService = Depends(get_daily_prize_service)) -> None:
    prizes.deliver(spin_id)


@router.post("/week-prizes/{child_id}/{end}/deliver", status_code=204)
def deliver_week_prize(child_id: str, end: str, streaks: StreaksService = Depends(get_streaks_service)) -> None:
    """Entregado: the prize of a full week (or the smaller one) handed over."""
    streaks.deliver_week_prize(child_id, end)
