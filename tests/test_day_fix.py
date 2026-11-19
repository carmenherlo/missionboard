"""Arreglar un día (19/11): «Lo hizo», «No lo hizo» or «Libre» for a day of this week."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import PARENT
from tests.test_missions import create_child
from tests.test_settings import FixedClock
from tests.test_today import MONDAY, check, descriptions, mission, today
from tests.test_week import week

MON = "2026-11-02"


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


def fix(client, child, day, choice, headers=PARENT):
    return client.put(f"/api/children/{child['id']}/days/{day}", json={"choice": choice}, headers=headers)


def monday_tank(client, child):
    return week(client, child)["tanks"][0]["state"]


def test_it_needs_the_code_and_a_known_choice(client, bea):
    assert fix(client, bea, MON, "done", headers={}).status_code == 401
    assert fix(client, bea, MON, "maybe").status_code == 422


def test_they_forgot_to_sign_yesterday(client, bea, clock):
    mission(client, bea, "Despegue", steps=("Uno",))
    clock.moment = MONDAY + timedelta(days=1)
    stars = today(client, bea)["stars"]
    assert monday_tank(client, bea) == "missed"
    assert fix(client, bea, MON, "done").status_code == 204
    assert monday_tank(client, bea) == "full"
    assert today(client, bea)["stars"] == stars + 1
    assert descriptions(client, limit=1)[0].startswith("Marcaste «Despegue» de Bea como hecha")
    assert fix(client, bea, MON, "done").status_code == 204  # again: nothing more
    assert today(client, bea)["stars"] == stars + 1


def test_not_done_undoes_its_missions(client, bea, clock):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    check(client, bea, item, 0)
    clock.moment = MONDAY + timedelta(days=1)
    stars = today(client, bea)["stars"]
    assert fix(client, bea, MON, "missed").status_code == 204
    assert monday_tank(client, bea) == "missed"
    assert today(client, bea)["stars"] == stars - 1


def test_free_and_back(client, bea, clock):
    mission(client, bea, "Despegue", steps=("Uno",))
    clock.moment = MONDAY + timedelta(days=1)
    assert fix(client, bea, MON, "free").status_code == 204
    assert monday_tank(client, bea) == "free"
    assert fix(client, bea, MON, "done").status_code == 204
    assert monday_tank(client, bea) == "full"


def test_a_day_ahead_can_only_be_let_off(client, bea):
    mission(client, bea, "Despegue", steps=("Uno",))
    tuesday = "2026-11-03"
    assert fix(client, bea, tuesday, "done").status_code == 409
    assert fix(client, bea, tuesday, "free").status_code == 204
