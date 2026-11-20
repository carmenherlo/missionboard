"""Arreglar un día (19/11): «Lo hizo», «No lo hizo» or «Libre» for a day of this week."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import PARENT
from tests.test_missions import create_child
from tests.test_settings import FixedClock
from tests.test_today import MONDAY, check, descriptions, mission, today
from tests.test_week import do_day, set_week, week

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


def test_a_week_closed_without_a_prize_can_still_be_fixed_until_the_next_one(client, bea, clock):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    clock.moment = MONDAY + timedelta(days=4)  # Friday, the prize day: only today done
    check(client, bea, item, 0)
    view = week(client, bea)
    assert view["result"]["tier"] == "none"
    client.post(f"/api/children/{bea['id']}/week/{view['result']['end']}/seen")  # as the child's screen does
    for day in ("2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05"):
        assert fix(client, bea, day, "done").status_code == 204
    assert week(client, bea)["result"]["tier"] == "full"  # the rocket can take off now


def test_a_week_that_took_off_can_be_fixed_till_the_next_one_starts(client, bea, clock):
    """Alex, 20/11: off with the smaller prize (3 of 5); then days changed. The rocket only
    takes off again for a better prize; from Monday, nothing changes."""
    set_week(client, second_on=True)
    item = mission(client, bea, "Despegue", steps=("Uno",))
    for offset in (0, 2, 4):
        do_day(client, bea, item, clock, offset)
    fri = "2026-11-06"
    assert fix(client, bea, fri, "missed").status_code == 204  # settled again: 2 of 5, nothing
    assert fix(client, bea, fri, "done").status_code == 204
    view = week(client, bea)
    assert view["result"]["tier"] == "second"
    client.post(f"/api/children/{bea['id']}/week/{fri}/seen")  # the rocket took off
    assert fix(client, bea, "2026-11-03", "free").status_code == 204  # 3 of 4: the same prize, not again
    assert week(client, bea)["took_off"] is True
    assert fix(client, bea, "2026-11-05", "done").status_code == 204
    view = week(client, bea)
    assert (view["took_off"], view["result"]["tier"]) == (False, "full")  # better: ready to go again
    clock.moment = MONDAY + timedelta(days=5)  # Saturday: still that week
    assert fix(client, bea, fri, "done").status_code == 204
    clock.moment = MONDAY + timedelta(days=7)  # Monday: the next one has started
    assert fix(client, bea, fri, "missed").status_code == 409


def test_days_let_off_after_the_week_closed_settle_it_again(client, bea, clock):
    """Noa, 20/11: only Friday done, the week closed without a prize; then Monday to
    Thursday are let off (ill): one tank of one, the big prize."""
    item = mission(client, bea, "Despegue", steps=("Uno",))
    clock.moment = MONDAY + timedelta(days=4)
    check(client, bea, item, 0)
    end = week(client, bea)["result"]["end"]
    client.post(f"/api/children/{bea['id']}/week/{end}/seen")
    for day in ("2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05"):
        assert fix(client, bea, day, "free").status_code == 204
    view = week(client, bea)
    assert (view["result"]["tier"], view["full"], view["counted"]) == ("full", 1, 1)


def test_once_the_rocket_took_off_the_week_says_so(client, bea, clock):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    for offset in range(5):
        do_day(client, bea, item, clock, offset)
    view = week(client, bea)
    assert view["took_off"] is False and view["result"]["tier"] == "full"
    client.post(f"/api/children/{bea['id']}/week/{view['result']['end']}/seen")
    assert week(client, bea)["took_off"] is True
