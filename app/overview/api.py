"""Padres · Hoy and Padres · Niño (step 7), with the parents' code."""

from fastapi import APIRouter, Depends

from app.children import avatars
from app.children.api import public_child
from app.children.repository import ChildrenRepository
from app.deps import get_clock, get_config_store, get_event_log, get_image_libraries, require_parent
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.missions.repository import MissionsRepository
from app.overview.service import OverviewService
from app.parents.repository import DEFAULT_PARENT_CODE, ParentsRepository
from app.prizes.repository import PrizesRepository
from app.routines.repository import RoutinesRepository
from app.shop.repository import ShopRepository
from app.settings import SettingsRepository
from app.shop.api import Presenter as ShopPresenter
from app.shop.api import get_orders_service
from app.shop.orders import OrdersService
from app.storage.config_store import ConfigStore
from app.today.api import Presenter as DayPresenter
from app.today.api import get_day_repository, get_day_service
from app.today.repository import DayRepository
from app.today.service import DayService, Today

router = APIRouter(prefix="/api/overview", tags=["overview"], dependencies=[Depends(require_parent)])


def get_overview_service(
    days: DayService = Depends(get_day_service),
    records: DayRepository = Depends(get_day_repository),
    orders: OrdersService = Depends(get_orders_service),
    store: ConfigStore = Depends(get_config_store),
    clock=Depends(get_clock),
    events: EventLog = Depends(get_event_log),
) -> OverviewService:
    return OverviewService(days, records, orders, ChildrenRepository(store), SettingsRepository(store), clock, events)


class Presenter:
    def __init__(self, libraries: ImageLibraries = Depends(get_image_libraries), day: DayPresenter = Depends(),
                 shop: ShopPresenter = Depends()):
        self._libraries = libraries
        self._day = day
        self._shop = shop

    def child_day(self, today: Today) -> dict:
        """The child's day as their own screen gets it, without what only the route needs."""
        full = self._day(today)
        return {
            "child": public_child(today.child),
            "colors": avatars.tones(today.child.color),
            "stars": today.stars,
            "streak": today.streak,
            "missions": [{k: m[k] for k in ("id", "name", "image_url", "state", "schedule", "done", "total")}
                         for m in full["missions"]],
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
        "children": [present.child_day(today) for today in view["children"]],
        "orders": [present.order(o) for o in view["orders"]],
        "prizes": [present.prize(p) for p in view["prizes"]],
    }


@router.get("/setup")
def setup(overview: OverviewService = Depends(get_overview_service), store: ConfigStore = Depends(get_config_store)):
    """Primeros pasos (Zona de padres): children, missions, switched on for someone, the code changed."""
    return overview.setup(
        MissionsRepository(store).list(),
        ParentsRepository(store).code() == DEFAULT_PARENT_CODE,
        len(PrizesRepository(store).list()), len(ShopRepository(store).list()), len(RoutinesRepository(store).list()))


@router.get("/children/{child_id}")
def overview_child(child_id: str, overview: OverviewService = Depends(get_overview_service),
                   present: Presenter = Depends()):
    view = overview.child(child_id)
    return {**present.child_day(view["today"]), "chart": view["chart"], "movements": view["movements"]}


@router.post("/prizes/{spin_id}/deliver", status_code=204)
def deliver_prize(spin_id: int, overview: OverviewService = Depends(get_overview_service)) -> None:
    overview.deliver_prize(spin_id)
