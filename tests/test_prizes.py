import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage.config_migrations import CURRENT_VERSION
from app.storage.config_store import config_path
from tests.conftest import PARENT
from tests.test_missions import PNG, create_child, photo_files, saved, upload
from tests.test_today import MONDAY, check, descriptions, mission, note, today, write_config
from tests.test_settings import FixedClock

SAMPLES = ["Guerra de cojines", "Elegir la cena", "Un cuento más", "15 minutos más de juego"]


@pytest.fixture
def clock():
    return FixedClock(MONDAY)


@pytest.fixture
def client(data_dir, clock):
    with TestClient(create_app(data_dir, clock=clock)) as c:
        yield c


@pytest.fixture
def bea(client):
    return create_child(client, preset="unicorn")


def texts(items):
    return [item["text"] for item in items]


def spin(client, child):
    return client.post(f"/api/children/{child['id']}/today/prize/spin")


def finish(client, child, item):
    for index in range(len(item["steps"])):
        check(client, child, item, index)


# ---------- the list, in Configurar ----------


def test_a_new_install_has_four_sample_prizes(client):
    prizes = client.get("/api/prizes").json()
    assert texts(prizes) == SAMPLES
    assert prizes[0]["image"] is None
    assert prizes[1]["image_url"].endswith("/pizza.svg")


def test_add_edit_and_delete_a_prize(client, data_dir):
    created = client.post("/api/prizes", json={"text": "  Ver una peli  "}, headers=PARENT)
    assert created.status_code == 201
    prize = created.json()
    assert prize["text"] == "Ver una peli"
    url = f"/api/prizes/{prize['id']}"
    changes = {"text": "Peli en el sofá", "image": "fluent/popcorn"}
    assert client.patch(url, json=changes, headers=PARENT).status_code == 200
    got = client.get(url).json()
    assert got["text"] == "Peli en el sofá" and got["image"] == "fluent/popcorn" and got["image_suggested"] is False
    assert client.delete(url, headers=PARENT).status_code == 204
    assert texts(client.get("/api/prizes").json()) == SAMPLES
    assert texts(saved(data_dir)["prizes"]) == SAMPLES


def test_a_new_prize_gets_a_suggested_image(client):
    prize = client.post("/api/prizes", json={"text": "Pizza para cenar"}, headers=PARENT).json()
    assert prize["image"] is not None and prize["image_suggested"] is True


def test_a_photo_replaces_the_old_one(client, data_dir):
    url = "/api/prizes/elegir-la-cena"
    upload(client, f"{url}/photo", PNG, "image/png")
    upload(client, f"{url}/photo", PNG, "image/png")
    assert len(photo_files(data_dir)) == 1
    client.delete(url, headers=PARENT)
    assert photo_files(data_dir) == []


@pytest.mark.parametrize("body", [{"text": ""}, {"text": "x" * 41}])
def test_a_bad_prize_is_refused(client, body):
    assert client.post("/api/prizes", json=body, headers=PARENT).status_code == 422


@pytest.mark.parametrize("call", [
    lambda c: c.post("/api/prizes", json={"text": "X"}),
    lambda c: c.patch("/api/prizes/mas-juego", json={"text": "X"}),
    lambda c: c.delete("/api/prizes/mas-juego"),
])
def test_changes_need_the_parent_code(client, call):
    assert call(client).status_code == 401


def test_changes_go_to_the_log(client):
    client.post("/api/prizes", json={"text": "Ver una peli"}, headers=PARENT)
    client.patch("/api/prizes/mas-juego", json={"text": "Más juego"}, headers=PARENT)
    client.delete("/api/prizes/un-cuento-mas", headers=PARENT)
    assert descriptions(client, limit=3) == [
        "Borraste el premio «Un cuento más»",
        "Cambiaste el premio «Más juego» · nombre: Más juego",
        "Añadiste el premio «Ver una peli»",
    ]


# ---------- the prize at the end of the route ----------


def test_locked_until_every_mission_of_today_is_done(client, bea):
    uno, dos = mission(client, bea, "Uno"), mission(client, bea, "Dos")
    assert today(client, bea)["prize"]["state"] == "locked"
    assert spin(client, bea).status_code == 409
    finish(client, bea, uno)
    assert today(client, bea)["prize"]["state"] == "locked"
    finish(client, bea, dos)
    prize = today(client, bea)["prize"]
    assert prize["state"] == "unlocked" and prize["spins_left"] == 1
    assert texts(prize["wheel"]) == SAMPLES
    assert prize["image_url"].endswith("/wrapped-gift.svg")


def test_a_closed_mission_means_no_prize_today(client, bea):
    mission(client, bea, "Deberes", schedule={"start": "15:00", "end": "17:00"})  # 17:10: closed
    hecha = mission(client, bea, "Merienda")
    finish(client, bea, hecha)
    assert today(client, bea)["prize"]["state"] == "locked"


def test_spinning_gives_one_prize_a_day(client, bea, clock):
    finish(client, bea, mission(client, bea, "Uno"))
    response = spin(client, bea)
    assert response.status_code == 200
    body = response.json()
    prize = body["today"]["prize"]
    assert prize["state"] == "won" and prize["spins_left"] == 0
    assert [w["prize_id"] for w in prize["won"]] == [body["prize_id"]]
    assert prize["won"][0]["text"] in SAMPLES
    assert spin(client, bea).status_code == 409
    assert descriptions(client, limit=1) == [f"Bea giró la ruleta · {prize['won'][0]['text']}"]

    clock.moment = MONDAY.replace(day=3)  # Tuesday: a new day, locked again
    assert today(client, bea)["prize"]["state"] == "locked"


def test_the_prize_won_keeps_its_name_if_the_prize_changes(client, bea):
    finish(client, bea, mission(client, bea, "Uno"))
    won = spin(client, bea).json()["prize_id"]
    client.patch(f"/api/prizes/{won}", json={"text": "Otro nombre"}, headers=PARENT)
    assert today(client, bea)["prize"]["won"][0]["text"] in SAMPLES


def test_more_spins_a_day_in_the_settings(data_dir, clock):
    write_config(data_dir, {"daily_prize_spins": 2})
    with TestClient(create_app(data_dir, clock=clock)) as client:
        bea = create_child(client)
        finish(client, bea, mission(client, bea, "Uno"))
        spin(client, bea)
        assert today(client, bea)["prize"]["state"] == "unlocked"
        spin(client, bea)
        assert len(today(client, bea)["prize"]["won"]) == 2
        assert spin(client, bea).status_code == 409


@pytest.mark.parametrize("settings", [{"features": {"daily_prize": False}}, {"prizes": []}])
def test_no_prize_on_the_route(data_dir, clock, settings):
    data_dir.mkdir(parents=True)
    doc = {"version": CURRENT_VERSION}
    doc["prizes"] = settings.get("prizes", [{"id": "p", "text": "Algo"}])
    doc["features"] = settings.get("features", {})
    config_path(data_dir).write_text(yaml.safe_dump(doc))
    with TestClient(create_app(data_dir, clock=clock)) as client:
        bea = create_child(client)
        mission(client, bea, "Uno")
        assert today(client, bea)["prize"] is None


def test_no_missions_today_no_prize(client, bea):
    assert today(client, bea)["prize"] is None


def test_touching_the_locked_prize_is_logged(client, bea):
    uno = mission(client, bea, "Uno")
    assert note(client, bea, "prize_locked", {"id": None}).status_code == 204
    assert descriptions(client, limit=1) == ["Bea tocó el premio, aún bloqueado"]
    finish(client, bea, uno)
    note(client, bea, "prize_locked", {"id": None})  # unlocked now: nothing to log
    assert descriptions(client, limit=1) == ["Bea desbloqueó el premio del día"]
