"""Deshacer una misión marcada por error (dias-libres.html, section 6)."""

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


def url(child, item, day="2026-11-02"):
    return f"/api/children/{child['id']}/missions/{item['id']}/days/{day}/undo"


def chest(client, child):
    return client.get(f"/api/children/{child['id']}/vouchers").json()["cards"]


def test_undo_needs_the_code_and_a_mission_done(client, bea):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    assert client.post(url(bea, item), json={}).status_code == 401
    assert client.get(url(bea, item), headers=PARENT).status_code == 404


def test_undo_takes_back_the_mission_its_star_and_the_card(client, bea):
    item = mission(client, bea, "Despegue", steps=("Uno", "Dos"))
    check(client, bea, item, 0)
    check(client, bea, item, 1)
    assert spin(client, bea).status_code == 200
    stars = today(client, bea)["stars"]
    preview = client.get(url(bea, item), headers=PARENT).json()
    assert (preview["reopens"], preview["stars"], len(preview["cards"])) == (True, 1, 1)
    assert client.post(url(bea, item), json={}, headers=PARENT).status_code == 200
    day = today(client, bea)
    assert states(client, bea) == {"Despegue": "open"}
    assert day["missions"][0]["done"] == 0 and day["stars"] == stars - 1
    assert day["prize"]["state"] == "locked" and chest(client, bea) == []
    assert any(d.startswith("Deshiciste «Despegue» de Bea") for d in descriptions(client))
    check(client, bea, item, 0)
    assert check(client, bea, item, 1).json()["stars_earned"] == 1  # done for real: its star again


def test_the_card_can_stay_and_stars_never_go_below_zero(client, bea):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    check(client, bea, item, 0)
    spin(client, bea)
    stars = today(client, bea)["stars"]
    client.post(f"/api/children/{bea['id']}/stars/take", json={"stars": stars}, headers=PARENT)  # all spent
    assert client.get(url(bea, item), headers=PARENT).json()["stars"] == 0
    client.post(url(bea, item), json={"keep_card": True}, headers=PARENT)
    assert today(client, bea)["stars"] == 0 and len(chest(client, bea)) == 1


def test_a_day_gone_by_of_this_week_closes_and_its_fuel_goes_back(client, bea, clock):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    check(client, bea, item, 0)
    assert client.post(f"/api/children/{bea['id']}/week/fuel/2026-11-02").status_code == 200
    clock.moment = MONDAY + timedelta(days=1)
    listed = client.get(f"/api/children/{bea['id']}/undoable", headers=PARENT).json()
    assert [(d["day"], d["name"]) for d in listed] == [("2026-11-02", "Despegue")]
    assert client.get(url(bea, item), headers=PARENT).json()["tank"] is True
    client.post(url(bea, item), json={}, headers=PARENT)
    week = client.get(f"/api/children/{bea['id']}/week").json()
    assert week["tanks"][0]["state"] == "missed" and not week["tanks"][0]["loaded"]


def test_last_weeks_days_are_not_undone(client, bea, clock):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    check(client, bea, item, 0)
    clock.moment = MONDAY + timedelta(days=7)
    assert client.get(url(bea, item), headers=PARENT).status_code == 409
    assert client.get(f"/api/children/{bea['id']}/undoable", headers=PARENT).json() == []
