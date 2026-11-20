"""Gift cards and the momento de vales (vales-2.html).

Every prize won on the wheel is a gift card in the child's chest until it is used: no
data of its own, it is the prize not delivered yet. A week's prize is not a card (20/11:
it is weekly, the cards are daily): it waits in the parents' «Premios de la semana».
A parent opens a momento de vales whenever they like; while it lasts, each child picks
one card from their chest, and that hands its prize over."""

from datetime import timedelta
from types import SimpleNamespace

from app.children.repository import ChildrenRepository
from app.clock import Clock
from app.daily_prize.repository import PrizeSpinsRepository
from app.errors import ConflictError, NotFoundError
from app.events.service import EventLog
from app.streaks.repository import StreaksRepository
from app.vouchers.repository import MomentsRepository

MOMENT_MINUTES = 30  # a moment closes by itself after this, so it is not left open
PICKS_PER_MOMENT = 1  # each child picks this many cards in a moment


class VouchersService:
    def __init__(
        self,
        spins: PrizeSpinsRepository,
        streaks: StreaksRepository,
        moments: MomentsRepository,
        children: ChildrenRepository,
        clock: Clock,
        events: EventLog,
    ):
        self._spins = spins
        self._streaks = streaks
        self._moments = moments
        self._children = children
        self._clock = clock
        self._events = events

    def cards(self, child_id: str) -> list[dict]:
        """The child's gift cards not used yet, oldest first."""
        return [
            {
                "id": f"spin-{row['id']}",
                "source": "wheel",
                "text": row["prize_text"],
                "image": row["prize_image"],
                "day": row["day"],
            }
            for row in self._spins.to_give()
            if row["child_id"] == child_id
        ]

    def moment(self) -> dict | None:
        """The momento de vales open now: until when, and who picked what."""
        moment = self._moments.current(self._clock.now())
        if moment is None:
            return None
        return {"id": moment["id"], "ends_at": moment["ends_at"], "picks": self._moments.picks(moment["id"])}

    def chest(self, child_id: str) -> dict:
        """What the child's chest shows: their cards, and whether they can pick one now."""
        child = self._children.require(child_id)
        moment = self.moment()
        picked = [p for p in moment["picks"] if p["child_id"] == child.id] if moment else []
        return {
            "cards": self.cards(child.id),
            "moment": moment and {"ends_at": moment["ends_at"], "can_pick": len(picked) < PICKS_PER_MOMENT},
        }

    def for_parents(self) -> dict:
        return {
            "children": [{"child": child, "cards": self.cards(child.id)} for child in self._children.list()],
            "moment": self.moment(),
        }

    def start_moment(self) -> None:
        now = self._clock.now()
        self._moments.start(now, now + timedelta(minutes=MOMENT_MINUTES))
        self._events.config_changed("vouchers", "moment_started")

    def end_moment(self) -> None:
        if self._moments.end(self._clock.now()):
            self._events.config_changed("vouchers", "moment_ended")

    def pick(self, child_id: str, card_id: str) -> None:
        """The child picks a card in the momento de vales: its prize is handed over."""
        child = self._children.require(child_id)
        moment = self.moment()
        if moment is None:
            raise ConflictError("It is not a momento de vales")
        if sum(p["child_id"] == child.id for p in moment["picks"]) >= PICKS_PER_MOMENT:
            raise ConflictError("Already picked in this moment")
        card = self._card(child.id, card_id)
        self._deliver(card_id)
        self._moments.add_pick(moment["id"], child, card, self._clock.now())
        self._events.child_did("voucher_used", child, prize=card["text"])

    def remove(self, child_id: str, card_id: str) -> None:
        """A parent takes a card out of the chest (given without the tablet, or not to be
        given). Its prize is kept as handed over, so the history stays."""
        child = self._children.require(child_id)
        card = self._card(child.id, card_id)
        self._deliver(card_id)
        self._events.config_changed("voucher", "removed", child=child, mission=_named(card_id, card["text"]))

    def undo(self, pick_id: int) -> None:
        """A card picked by mistake goes back to the chest."""
        pick = self._moments.pick(pick_id)
        if pick is None:
            raise NotFoundError("Pick not found")
        kind, ref = _split(pick["voucher_id"])
        if kind == "spin":
            self._spins.undeliver(int(ref))
        else:  # a week's prize picked before 20/11, when it was a card
            self._streaks.undeliver_week_prize(pick["child_id"], ref)
        self._moments.remove_pick(pick_id)
        self._events.config_changed(
            "voucher",
            "undone",
            child=SimpleNamespace(id=pick["child_id"], name=pick["child_name"]),
            mission=_named(pick["voucher_id"], pick["prize_text"]),
        )

    def _card(self, child_id: str, card_id: str) -> dict:
        card = next((c for c in self.cards(child_id) if c["id"] == card_id), None)
        if card is None:
            raise NotFoundError("Gift card not found")
        return card

    def _deliver(self, card_id: str) -> None:
        self._spins.deliver(int(_split(card_id)[1]), self._clock.now())


def _split(card_id: str) -> tuple[str, str]:
    kind, _, ref = card_id.partition("-")
    return kind, ref


def _named(card_id: str, text: str) -> SimpleNamespace:
    return SimpleNamespace(id=card_id, name=text)
