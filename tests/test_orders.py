"""A purchase as an order on its way (tienda-2.html): the child's and the parents' side,
and the parents' phones through Home Assistant (faked)."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import PARENT
from tests.test_missions import create_child
from tests.test_settings import FixedClock
from tests.test_shop import buy, earn, shop
from tests.test_today import MONDAY, descriptions


class FakeHomeAssistant:
    available = True

    def __init__(self):
        self.sent = []

    def phones(self):
        return ["mobile_app_mum", "mobile_app_dad"]

    def send(self, phones, title, message, actions, tag):
        self.sent.append({"phones": phones, "title": title, "message": message,
                          "actions": [a for a, _ in actions], "tag": tag})

    async def listen(self, on_action):
        pass


@pytest.fixture
def clock():
    return FixedClock(MONDAY)


@pytest.fixture
def ha():
    return FakeHomeAssistant()


@pytest.fixture
def app(data_dir, clock, ha):
    app = create_app(data_dir, clock=clock)
    app.state.home_assistant = ha
    return app


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def bea(client):
    return create_child(client)


def ordered(client, child, item="elegir-postre", stars=3):
    earn(client, child, stars)
    return buy(client, child, item).json()["order_id"]


def mine(client, child):
    return shop(client, child)["orders"]


def with_phones(client):
    client.patch("/api/settings", json={"shop_notify": {"phones": ["mobile_app_mum"], "remind_at": "18:00"}},
                 headers=PARENT)


def test_an_order_is_on_its_way_until_a_parent_hands_it_over(client, bea):
    order_id = ordered(client, bea)
    [order] = mine(client, bea)
    assert (order["state"], order["nights"], order["progress"]) == ("on_way", None, 0.15)
    assert client.get("/api/orders/summary").json() == {bea["id"]: {"on_way": 1, "arrived": 0, "today": [], "arrived_ids": []}}
    assert [o["id"] for o in client.get("/api/orders", headers=PARENT).json()["waiting"]] == [order_id]

    assert client.post(f"/api/orders/{order_id}/deliver", headers=PARENT).json()["state"] == "arrived"
    assert client.get("/api/orders/summary").json() == {bea["id"]: {"on_way": 0, "arrived": 1, "today": [], "arrived_ids": [order_id]}}
    assert descriptions(client, limit=1) == ["Entregaste «Elegir el postre» a Bea"]

    assert client.post(f"/api/children/{bea['id']}/orders/{order_id}/seen").status_code == 204
    assert mine(client, bea)[0]["state"] == "done"
    assert client.get("/api/orders/summary").json() == {}
    assert client.get("/api/orders", headers=PARENT).json()["handed"][0]["id"] == order_id


def test_the_day_it_arrives_moves_the_truck(client, bea, clock):
    order_id = ordered(client, bea)
    due = (MONDAY + timedelta(days=2)).date().isoformat()
    changed = client.patch(f"/api/orders/{order_id}", json={"due_day": due}, headers=PARENT).json()
    assert (changed["nights"], changed["progress"]) == (2, 0.1)
    assert descriptions(client, limit=1) == ["Dijiste cuándo le llega «Elegir el postre» a Bea · llega el 4/11"]
    clock.moment = MONDAY + timedelta(days=1)
    assert (mine(client, bea)[0]["nights"], mine(client, bea)[0]["progress"]) == (1, 0.475)
    clock.moment = MONDAY + timedelta(days=5)  # late: it stays almost home
    assert (mine(client, bea)[0]["nights"], mine(client, bea)[0]["progress"]) == (0, 0.85)


def test_orders_need_the_code_and_children_see_only_their_own(client, bea):
    order_id = ordered(client, bea)
    assert client.get("/api/orders").status_code == 401
    assert client.post(f"/api/orders/{order_id}/deliver").status_code == 401
    assert client.post(f"/api/orders/{order_id + 9}/deliver", headers=PARENT).status_code == 404
    assert client.post(f"/api/children/other/orders/{order_id}/seen").status_code == 404


def test_buying_tells_the_chosen_phones(client, bea, ha):
    with_phones(client)
    order_id = ordered(client, bea)
    [message] = ha.sent
    assert message["phones"] == ["mobile_app_mum"]
    assert message["title"] == "🛒 Bea ha pedido «Elegir el postre»"
    assert message["actions"] == [f"MISSIONBOARD_ORDER_{order_id}_{a}" for a in ("TODAY", "TOMORROW", "GIVEN")]


def test_the_phone_buttons(client, app, bea):
    from app.main import _orders

    order_id = ordered(client, bea)
    assert _orders(app).on_action(f"MISSIONBOARD_ORDER_{order_id}_TOMORROW")
    assert mine(client, bea)[0]["nights"] == 1
    assert _orders(app).on_action(f"MISSIONBOARD_ORDER_{order_id}_GIVEN")
    assert mine(client, bea)[0]["state"] == "arrived"
    assert not _orders(app).on_action("SOMETHING_ELSE")
    assert not _orders(app).on_action("MISSIONBOARD_ORDER_999_GIVEN")


def test_a_reminder_on_the_day_it_was_due_once(client, app, bea, ha, clock):
    from app.main import _orders

    with_phones(client)
    order_id = ordered(client, bea)
    client.patch(f"/api/orders/{order_id}", json={"due_day": MONDAY.date().isoformat()}, headers=PARENT)
    ha.sent.clear()
    clock.moment = MONDAY.replace(hour=17, minute=59)
    _orders(app).remind()
    assert ha.sent == []
    clock.moment = MONDAY.replace(hour=18, minute=0)
    _orders(app).remind()
    _orders(app).remind()
    assert [m["title"] for m in ha.sent] == ["🚚 Hoy llega «Elegir el postre» de Bea"]
    clock.moment = MONDAY + timedelta(days=1, hours=2)  # still not handed over: again the next day
    _orders(app).remind()
    assert len(ha.sent) == 2


def test_the_phones_of_home_assistant(client):
    assert client.get("/api/notify/phones", headers=PARENT).json() == {
        "available": True, "phones": ["mobile_app_mum", "mobile_app_dad"]}


def test_without_home_assistant_nothing_is_sent(data_dir, clock):
    with TestClient(create_app(data_dir, clock=clock)) as client:
        bea = create_child(client)
        ordered(client, bea)
        assert client.get("/api/notify/phones", headers=PARENT).json() == {"available": False, "phones": []}


def test_the_summary_says_which_orders_arrive_today(client, bea):
    order_id = ordered(client, bea)
    today_ = MONDAY.date().isoformat()
    client.patch(f"/api/orders/{order_id}", json={"due_day": today_}, headers=PARENT)
    assert client.get("/api/orders/summary").json()[bea["id"]]["today"] == [order_id]
