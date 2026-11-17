"""Gift cards and the momento de vales (vales-2.html). The child's chest has no parent
code; opening a moment, marking a card used and undoing a pick have."""

from fastapi import APIRouter, Depends

from app.children import avatars
from app.children.api import public_child
from app.children.repository import ChildrenRepository
from app.daily_prize.repository import PrizeSpinsRepository
from app.deps import (
    get_clock,
    get_config_store,
    get_event_log,
    get_image_libraries,
    get_moments_repository,
    get_prize_spins_repository,
    get_streaks_repository,
    require_parent,
)
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.storage.config_store import ConfigStore
from app.streaks.repository import StreaksRepository
from app.vouchers.repository import MomentsRepository
from app.vouchers.service import VouchersService

router = APIRouter(prefix="/api", tags=["vouchers"])
parents = [Depends(require_parent)]


def get_vouchers_service(
    spins: PrizeSpinsRepository = Depends(get_prize_spins_repository),
    streaks: StreaksRepository = Depends(get_streaks_repository),
    moments: MomentsRepository = Depends(get_moments_repository),
    store: ConfigStore = Depends(get_config_store),
    clock=Depends(get_clock),
    events: EventLog = Depends(get_event_log),
) -> VouchersService:
    return VouchersService(spins, streaks, moments, ChildrenRepository(store), clock, events)


class Presenter:
    def __init__(self, libraries: ImageLibraries = Depends(get_image_libraries)):
        self._libraries = libraries

    def card(self, card: dict) -> dict:
        return {k: card[k] for k in ("id", "source", "text", "day")} | {"image_url": self._libraries.url(card["image"])}


@router.get("/children/{child_id}/vouchers")
def chest(child_id: str, vouchers: VouchersService = Depends(get_vouchers_service), present: Presenter = Depends()):
    """The child's chest: their gift cards, and whether a momento de vales lets them pick one."""
    view = vouchers.chest(child_id)
    return {"cards": [present.card(c) for c in view["cards"]], "moment": view["moment"]}


@router.post("/children/{child_id}/vouchers/{card_id}/pick", status_code=204)
def pick(child_id: str, card_id: str, vouchers: VouchersService = Depends(get_vouchers_service)) -> None:
    """In a momento de vales: the child picks this card (409 out of one, or picked already)."""
    vouchers.pick(child_id, card_id)


@router.get("/vouchers", dependencies=parents)
def for_parents(vouchers: VouchersService = Depends(get_vouchers_service), present: Presenter = Depends()):
    """Zona de padres · Hoy: every child's gift cards, and the moment open now with who picked what."""
    view = vouchers.for_parents()
    return {
        "children": [
            {
                "child": public_child(row["child"]),
                "colors": avatars.tones(row["child"].color),
                "cards": [present.card(c) for c in row["cards"]],
            }
            for row in view["children"]
        ],
        "moment": view["moment"],
    }


@router.post("/vouchers/moment", status_code=204, dependencies=parents)
def start_moment(vouchers: VouchersService = Depends(get_vouchers_service)) -> None:
    vouchers.start_moment()


@router.delete("/vouchers/moment", status_code=204, dependencies=parents)
def end_moment(vouchers: VouchersService = Depends(get_vouchers_service)) -> None:
    vouchers.end_moment()


@router.delete("/vouchers/picks/{pick_id}", status_code=204, dependencies=parents)
def undo_pick(pick_id: int, vouchers: VouchersService = Depends(get_vouchers_service)) -> None:
    vouchers.undo(pick_id)


@router.post("/children/{child_id}/vouchers/{card_id}/used", status_code=204, dependencies=parents)
def mark_used(child_id: str, card_id: str, vouchers: VouchersService = Depends(get_vouchers_service)) -> None:
    """A parent gave the prize without the tablet: the card leaves the chest."""
    vouchers.mark_used(child_id, card_id)
