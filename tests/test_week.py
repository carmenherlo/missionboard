"""Rachas: the week of fuel tanks (rachas.html)."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings.repository import StreakWeek
from app.today.week import build_week, week_end
from tests.conftest import PARENT
from tests.test_missions import create_child
from tests.test_settings import FixedClock
from tests.test_today import MONDAY, check, descriptions, mission

MON = date(2026, 11, 2)


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


def week(client, child):
    return client.get(f"/api/children/{child['id']}/week").json()


def rules(**changes):
    return {**StreakWeek().model_dump(mode="json"), **changes}


def set_week(client, **changes):
    response = client.patch("/api/settings", json={"streak_week": rules(**changes)}, headers=PARENT)
    assert response.status_code == 200, response.text


def do_day(client, child, item, clock, day_offset):
    clock.moment = MONDAY + timedelta(days=day_offset)
    check(client, child, item, 0)


# ---------- the rule ----------


def test_the_week_ends_on_the_prize_day():
    assert week_end(MON, "fri") == MON + timedelta(days=4)
    assert week_end(MON + timedelta(days=4), "fri") == MON + timedelta(days=4)
    assert week_end(MON + timedelta(days=5), "fri") == MON + timedelta(days=11)  # Saturday: next week


def test_tanks_are_the_days_that_count_with_missions():
    sw = StreakWeek(days=("sun", "mon", "tue", "wed", "thu", "fri"))
    had = lambda d: {"a"}  # noqa: E731
    wed = MON + timedelta(days=2)
    done = {(MON - timedelta(days=1)).isoformat(): {"a"}, MON.isoformat(): {"a"}}
    w = build_week(wed, week_end(wed, "fri"), sw, "all", had, done, free={(MON + timedelta(days=1)).isoformat()})
    assert [(t.letter, t.state) for t in w.tanks] == [
        ("D", "full"), ("L", "full"), ("M", "free"), ("X", "now"), ("J", "later"), ("V", "later")]
    assert (w.full, w.counted, w.closed) == (2, 5, False)


def test_a_closed_week_has_a_tier():
    had = lambda d: {"a"}  # noqa: E731
    fri = MON + timedelta(days=4)
    done = {(MON + timedelta(days=n)).isoformat(): {"a"} for n in (0, 1, 2)}
    sw = StreakWeek()
    w = build_week(fri + timedelta(days=1), fri, sw, "all", had, done, set())
    assert w.closed and w.tier(sw) == "none"
    assert w.tier(StreakWeek(second_on=True, second_min=3)) == "second"
    done |= {(MON + timedelta(days=n)).isoformat(): {"a"} for n in (3, 4)}
    assert build_week(fri, fri, sw, "all", had, done, set()).tier(sw) == "full"


# ---------- the child's week ----------


def test_a_full_week_wins_the_prize_for_the_parents_to_give(client, bea, clock):
    set_week(client, prize="Ir al parque")
    item = mission(client, bea, "Despegue", steps=("Uno",))
    for n in range(4):
        do_day(client, bea, item, clock, n)
    view = week(client, bea)
    assert [t["state"] for t in view["tanks"]] == ["full"] * 4 + ["later"] and view["result"] is None
    do_day(client, bea, item, clock, 4)  # Friday, the prize day
    view = week(client, bea)
    assert view["result"] == {"end": "2026-11-06", "tier": "full", "prize_text": "Ir al parque", "full": 5, "counted": 5}
    assert descriptions(client, limit=5)[0] == "Bea llenó todos los depósitos de la semana · 5 de 5"

    [prize] = client.get("/api/overview/today", headers=PARENT).json()["week_prizes"]
    assert prize["prize_text"] == "Ir al parque"
    url = f"/api/overview/week-prizes/{bea['id']}/2026-11-06/deliver"
    assert client.post(url, headers=PARENT).status_code == 204
    assert client.get("/api/overview/today", headers=PARENT).json()["week_prizes"] == []

    assert client.post(f"/api/children/{bea['id']}/week/2026-11-06/seen").status_code == 204
    assert week(client, bea)["result"] is None


def test_a_week_short_of_fuel_has_no_prize_but_the_smaller_one_can_be_won(client, bea, clock):
    set_week(client, second_on=True, second_min=3, second="Un cuento más")
    item = mission(client, bea, "Despegue", steps=("Uno",))
    week(client, bea)  # Monday: the child comes in for the first time
    for n in (0, 1, 2):
        do_day(client, bea, item, clock, n)
    clock.moment = MONDAY + timedelta(days=5)  # Saturday: Thursday and Friday were missed
    result = week(client, bea)["result"]
    assert (result["tier"], result["prize_text"], result["full"]) == ("second", "Un cuento más", 3)


def test_a_day_off_neither_counts_nor_breaks_the_week(client, bea, clock):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    url = f"/api/children/{bea['id']}/free-days/2026-11-03"
    assert client.put(url, json={"free": True}).status_code == 401
    assert client.put(url, json={"free": True}, headers=PARENT).status_code == 204
    week(client, bea)
    for n in (0, 2, 3, 4):
        do_day(client, bea, item, clock, n)
    assert week(client, bea)["result"]["tier"] == "full"


def test_without_rachas_there_is_no_week(client, bea):
    client.patch("/api/settings/features", json={"streaks": False}, headers=PARENT)
    assert week(client, bea) == {"on": False}
