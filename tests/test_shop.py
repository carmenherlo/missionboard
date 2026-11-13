import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage.config_migrations import CURRENT_VERSION
from app.storage.config_store import config_path
from tests.conftest import PARENT
from tests.test_missions import create_child, saved
from tests.test_settings import FixedClock
from tests.test_today import MONDAY, check, descriptions, mission, today

SAMPLES = ["Elegir el postre", "Un globo", "Un peluche"]


@pytest.fixture
def clock():
    return FixedClock(MONDAY)


@pytest.fixture
def client(data_dir, clock):
    with TestClient(create_app(data_dir, clock=clock)) as c:
        yield c


@pytest.fixture
def bea(client):
    return create_child(client)


def earn(client, child, stars):
    """Complete missions of one step until the child has that many stars."""
    for n in range(stars):
        item = mission(client, child, f"M{n}", steps=("Paso",))
        check(client, child, item, 0)


def shop(client, child):
    return client.get(f"/api/children/{child['id']}/shop").json()


def buy(client, child, item_id):
    return client.post(f"/api/children/{child['id']}/shop/{item_id}/buy")


# ---------- Configurar → Tienda ----------


def test_a_new_install_has_three_sample_items(client):
    items = client.get("/api/shop").json()
    assert [i["text"] for i in items] == SAMPLES and [i["price"] for i in items] == [3, 5, 20]


def test_add_change_and_remove_an_item(client, data_dir):
    item = client.post("/api/shop", json={"text": " Ver una peli ", "price": 8}, headers=PARENT).json()
    assert item["text"] == "Ver una peli" and item["price"] == 8
    url = f"/api/shop/{item['id']}"
    changed = client.patch(url, json={"price": 6, "image": "fluent/popcorn"}, headers=PARENT).json()
    assert changed["price"] == 6 and changed["image"] == "fluent/popcorn"
    assert descriptions(client, limit=1) == [
        "Cambiaste «Ver una peli» de la tienda · imagen cambiada · precio: 6 estrellas"]
    assert client.delete(url, headers=PARENT).status_code == 204
    assert [i["text"] for i in saved(data_dir)["shop"]] == SAMPLES


@pytest.mark.parametrize("body", [{"text": "", "price": 3}, {"text": "X", "price": 0}, {"text": "X"}])
def test_a_bad_item_is_refused(client, body):
    assert client.post("/api/shop", json=body, headers=PARENT).status_code == 422


def test_changes_need_the_parent_code(client):
    assert client.post("/api/shop", json={"text": "X", "price": 1}).status_code == 401
    assert client.delete("/api/shop/globo").status_code == 401


# ---------- Mis estrellas ----------


def test_the_child_sees_their_stars_and_what_they_can_buy(client, bea):
    earn(client, bea, 4)
    view = shop(client, bea)
    assert view["stars"] == 4
    assert [(i["text"], i["affordable"]) for i in view["items"]] == [
        ("Elegir el postre", True), ("Un globo", False), ("Un peluche", False)]


def test_buying_takes_the_stars(client, bea):
    earn(client, bea, 4)
    response = buy(client, bea, "elegir-postre")
    assert response.status_code == 200
    view = response.json()
    assert view["stars"] == 1
    order = view["orders"][0]
    assert order["item_text"] == "Elegir el postre" and order["state"] == "on_way" and order["id"] == view["order_id"]
    assert today(client, bea)["stars"] == 1
    assert descriptions(client, limit=1) == ["Bea compró «Elegir el postre» · -3 estrellas"]


def test_not_enough_stars(client, bea):
    earn(client, bea, 2)
    assert buy(client, bea, "globo").status_code == 422
    assert shop(client, bea)["stars"] == 2 and shop(client, bea)["orders"] == []


def test_unknown_child_or_item(client, bea):
    assert buy(client, bea, "nope").status_code == 404
    assert client.get("/api/children/nobody/shop").status_code == 404


def test_the_shop_can_be_switched_off(data_dir, clock):
    data_dir.mkdir(parents=True)
    doc = {"version": CURRENT_VERSION, "shop": [{"id": "x", "text": "X", "price": 1}], "features": {"shop": False}}
    config_path(data_dir).write_text(yaml.safe_dump(doc))
    with TestClient(create_app(data_dir, clock=clock)) as client:
        bea = create_child(client)
        assert shop(client, bea)["items"] == []
        assert buy(client, bea, "x").status_code == 409
