"""Gift cards and the momento de vales (vales-2.html)."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.streaks.repository import StreaksRepository
from tests.conftest import PARENT
from tests.test_missions import create_child
from tests.test_prizes import spin
from tests.test_settings import FixedClock
from tests.test_today import MONDAY, check, descriptions, mission


@pytest.fixture
def clock():
    return FixedClock(MONDAY)


@pytest.fixture
def client(data_dir, clock):
    with TestClient(create_app(data_dir, clock=clock)) as c:
        yield c


@pytest.fixture
def bea(client):
    child = create_child(client)
    client.get(f"/api/children/{child['id']}/week")  # their racha starts today (Monday)
    return child


def win(client, child, item=None):
    """Do today's mission (a new one, or `item` on another day) and spin the wheel: a gift card."""
    item = item or mission(client, child, f"Misión {child['name']}", steps=("Uno",))
    check(client, child, item, 0)
    assert spin(client, child).status_code == 200
    return item


def chest(client, child):
    return client.get(f"/api/children/{child['id']}/vouchers").json()


def start(client):
    assert client.post("/api/vouchers/moment", headers=PARENT).status_code == 204


def pick(client, child, card):
    return client.post(f"/api/children/{child['id']}/vouchers/{card['id']}/pick")


def test_a_prize_of_the_wheel_is_a_gift_card_in_the_chest(client, bea):
    assert chest(client, bea) == {"cards": [], "moment": None}
    win(client, bea)
    [card] = chest(client, bea)["cards"]
    assert card["source"] == "wheel" and card["text"] and card["image_url"]


def test_out_of_a_moment_a_card_cannot_be_picked(client, bea):
    win(client, bea)
    [card] = chest(client, bea)["cards"]
    assert pick(client, bea, card).status_code == 409
    assert len(chest(client, bea)["cards"]) == 1


def test_in_a_moment_each_child_picks_one_card(client, bea):
    win(client, bea)
    start(client)
    view = chest(client, bea)
    assert view["moment"]["can_pick"] is True
    [card] = view["cards"]
    assert pick(client, bea, card).status_code == 204
    assert chest(client, bea) == {"cards": [], "moment": {"ends_at": view["moment"]["ends_at"], "can_pick": False}}
    assert descriptions(client, limit=1)[0] == f"Bea eligió su tarjeta regalo «{card['text']}»"
    # used, it is handed over: no longer waiting in Padres · Hoy
    assert client.get("/api/overview/today", headers=PARENT).json()["prizes"] == []


def test_one_card_per_moment(client, bea, clock):
    item = win(client, bea)
    clock.moment = MONDAY + timedelta(days=1)
    win(client, bea, item)
    start(client)
    first, second = chest(client, bea)["cards"]
    assert pick(client, bea, first).status_code == 204
    assert pick(client, bea, second).status_code == 409
    start(client)  # a new moment: one more
    assert pick(client, bea, second).status_code == 204


def test_a_moment_closes_by_itself_or_when_a_parent_ends_it(client, bea, clock):
    start(client)
    assert chest(client, bea)["moment"]
    clock.moment = MONDAY + timedelta(minutes=31)
    assert chest(client, bea)["moment"] is None
    start(client)
    assert client.delete("/api/vouchers/moment", headers=PARENT).status_code == 204
    assert chest(client, bea)["moment"] is None


def test_the_parents_see_every_card_and_who_picked_what_and_can_undo_it(client, bea):
    win(client, bea)
    start(client)
    [card] = chest(client, bea)["cards"]
    pick(client, bea, card)
    view = client.get("/api/vouchers", headers=PARENT).json()
    assert view["children"][0]["cards"] == []
    [picked] = view["moment"]["picks"]
    assert (picked["child_name"], picked["prize_text"]) == ("Bea", card["text"])
    assert client.delete(f"/api/vouchers/picks/{picked['id']}", headers=PARENT).status_code == 204
    assert [c["id"] for c in chest(client, bea)["cards"]] == [card["id"]]
    assert chest(client, bea)["moment"]["can_pick"] is True


def test_a_parent_removes_a_card_from_the_chest_and_the_parents_list(client, bea):
    win(client, bea)
    [card] = chest(client, bea)["cards"]
    url = f"/api/children/{bea['id']}/vouchers/{card['id']}"
    assert client.delete(url).status_code == 401
    assert client.delete(url, headers=PARENT).status_code == 204
    assert chest(client, bea)["cards"] == []
    assert client.get("/api/vouchers", headers=PARENT).json()["children"][0]["cards"] == []
    assert descriptions(client, limit=1)[0] == f"Eliminaste la tarjeta regalo «{card['text']}» de Bea"
    assert client.delete(url, headers=PARENT).status_code == 404


def test_the_parents_routes_need_the_code(client):
    assert client.get("/api/vouchers").status_code == 401
    assert client.post("/api/vouchers/moment").status_code == 401


def test_a_weeks_prize_is_not_a_card_it_waits_for_the_parents(client, bea, data_dir):
    streaks = StreaksRepository(data_dir)
    child = SimpleNamespace(id=bea["id"], name="Bea")
    streaks.freeze(child, "2026-10-30", "full", 5, 5, "", None, MONDAY)  # a week over, won
    streaks.launched(child, "2026-10-30", "full", "", None, MONDAY)  # the rocket took off
    assert chest(client, bea)["cards"] == []
    assert client.get("/api/vouchers", headers=PARENT).json()["children"][0]["cards"] == []
    [waiting] = client.get("/api/overview/today", headers=PARENT).json()["week_prizes"]
    assert waiting["week_end"] == "2026-10-30"
    url = f"/api/overview/week-prizes/{bea['id']}/2026-10-30/deliver"
    assert client.post(url, headers=PARENT).status_code == 204
    assert client.get("/api/overview/today", headers=PARENT).json()["week_prizes"] == []
