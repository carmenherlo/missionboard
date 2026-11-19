"""Días libres (dias-libres.html): a whole day or a mission let off, «hoy no toca»."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import PARENT
from tests.test_missions import create_child
from tests.test_prizes import spin
from tests.test_settings import FixedClock
from tests.test_today import MONDAY, check, descriptions, mission, states, today


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


def let_off(client, child, day="2026-11-02", **body):
    return client.put(f"/api/children/{child['id']}/day-offs/{day}", json=body, headers=PARENT)


def test_letting_off_needs_the_code(client, bea):
    assert client.put(f"/api/children/{bea['id']}/day-offs/2026-11-02", json={"whole": True}).status_code == 401
    assert client.get(f"/api/children/{bea['id']}/day-offs/2026-11-02").status_code == 401


def test_a_mission_let_off_does_not_block_the_prize(client, bea):
    first = mission(client, bea, "Despegue", steps=("Uno",))
    second = mission(client, bea, "Aterrizaje", steps=("Uno",))
    view = let_off(client, bea, missions=[first["id"]], phrase="Hoy vas de excursión").json()
    assert [(m["name"], m["off"]) for m in view["missions"]] == [("Despegue", True), ("Aterrizaje", False)]
    assert states(client, bea) == {"Despegue": "off", "Aterrizaje": "open"}
    assert check(client, bea, first, 0).status_code == 409  # off: nothing to check
    assert check(client, bea, second, 0).json()["stars_earned"] == 1
    day = today(client, bea)
    assert (day["prize"]["state"], day["day_off"], day["off_phrase"]) == ("unlocked", False, "Hoy vas de excursión")
    assert "Dejaste libre «Despegue» a Bea · el 2/11 · «Hoy vas de excursión»" in descriptions(client)


def test_a_whole_day_off_has_no_prize_and_does_not_break_the_streak(client, bea, clock):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    check(client, bea, item, 0)  # Monday done
    assert let_off(client, bea, "2026-11-03", whole=True).status_code == 200  # Tuesday, the day before
    clock.moment = MONDAY + timedelta(days=1)
    day = today(client, bea)
    assert (day["day_off"], day["prize"], day["missions"][0]["state"]) == (True, None, "off")
    clock.moment = MONDAY + timedelta(days=2)
    check(client, bea, item, 0)
    assert today(client, bea)["streak"] == 2
    tanks = client.get(f"/api/children/{bea['id']}/week").json()["tanks"]
    assert [t["state"] for t in tanks][:3] == ["full", "free", "full"]


def test_opening_a_mission_let_off_makes_it_count_again(client, bea):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    let_off(client, bea, missions=[item["id"]])
    client.post(f"/api/children/{bea['id']}/today/missions/{item['id']}/open", headers=PARENT)
    assert states(client, bea) == {"Despegue": "open"}


def test_what_is_done_wins_and_a_gone_day_is_not_changed_here(client, bea):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    check(client, bea, item, 0)
    let_off(client, bea, whole=True)
    assert states(client, bea) == {"Despegue": "done"}
    assert spin(client, bea).status_code == 200
    assert let_off(client, bea, "2026-11-01", whole=True).status_code == 422


def test_the_free_days_of_the_week_are_whole_days_off(client, bea):
    mission(client, bea, "Despegue", steps=("Uno",))
    url = f"/api/children/{bea['id']}/free-days/2026-11-02"
    assert client.put(url, json={"free": True}, headers=PARENT).status_code == 204
    assert today(client, bea)["day_off"] is True
    assert client.put(url, json={"free": False}, headers=PARENT).status_code == 204
    assert today(client, bea)["day_off"] is False


def test_the_old_free_days_move_to_day_offs(data_dir):
    from app.storage import db

    db.migrate(data_dir, db.MIGRATIONS[:14])
    with db.connect(data_dir) as conn:
        conn.execute("INSERT INTO free_days (child_id, day, at) VALUES ('bea', '2026-11-03', 'x')")
    db.migrate(data_dir)
    with db.connect(data_dir) as conn:
        rows = [tuple(r) for r in conn.execute("SELECT child_id, day, mission_id, phrase FROM day_offs")]
    assert rows == [("bea", "2026-11-03", "", "")]


def test_the_routine_does_not_wait_for_a_child_let_off_and_does_not_ring_if_all_are(data_dir):
    from tests.test_routines import MONDAY as MORNING
    from tests.test_routines import make_morning

    with TestClient(create_app(data_dir, clock=FixedClock(MORNING))) as client:
        bea, alex = create_child(client), create_child(client, name="Alex", preset="dinosaur")
        morning = make_morning(client)
        let_off(client, alex, missions=[morning["mission_id"]])
        routine = client.get("/api/routines/current").json()
        assert [p["child"]["name"] for p in routine["people"]] == ["Bea"]
        let_off(client, bea, whole=True)
        assert client.get("/api/routines/current").json() is None
