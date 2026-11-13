"""Padres · Hoy and Padres · Niño (step 7) and the streaks (step 8)."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.today.streaks import streak
from tests.conftest import PARENT
from tests.test_missions import create_child
from tests.test_prizes import spin
from tests.test_settings import FixedClock
from tests.test_today import MONDAY, check, descriptions, mission, today


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


def overview(client):
    return client.get("/api/overview/today", headers=PARENT).json()


# ---------- the streak, as a rule ----------

MON = date(2026, 11, 2)


def test_a_streak_counts_days_in_a_row_and_skips_days_without_missions():
    had = lambda d: set() if d.weekday() == 6 else {"a", "b"}  # nothing on Sundays  # noqa: E731
    done = {(MON - timedelta(days=n)).isoformat(): {"a"} for n in (1, 2, 3)}  # Sun, Sat, Fri
    assert streak(MON, "any", had, done) == 2  # Mon not yet: Sat and Fri (Sunday skipped)
    done[MON.isoformat()] = {"a", "b"}
    assert streak(MON, "any", had, done) == 3
    assert streak(MON, "all", had, done) == 1  # Saturday had only one of two


def test_the_childs_day_brings_their_streak(client, bea, clock):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    check(client, bea, item, 0)
    clock.moment = MONDAY + timedelta(days=1)
    assert today(client, bea)["streak"] == 1  # yesterday, and today not yet
    check(client, bea, item, 0)
    assert today(client, bea)["streak"] == 2
    client.patch("/api/settings/features", json={"streaks": False}, headers=PARENT)
    assert today(client, bea)["streak"] is None


# ---------- Padres · Hoy ----------


def test_today_shows_each_child_and_what_is_waiting(client, bea):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    check(client, bea, item, 0)
    spin(client, bea)
    view = overview(client)
    [child] = view["children"]
    assert child["child"]["name"] == "Bea" and child["streak"] == 1
    assert [(m["name"], m["state"]) for m in child["missions"]] == [("Despegue", "done")]
    assert child["prize"]["state"] == "won"
    [prize] = view["prizes"]
    assert client.post(f"/api/overview/prizes/{prize['id']}/deliver", headers=PARENT).status_code == 204
    assert overview(client)["prizes"] == []
    assert descriptions(client, limit=1)[0].startswith("Diste el premio «")


def test_today_needs_the_code(client):
    assert client.get("/api/overview/today").status_code == 401
    assert client.post("/api/overview/prizes/1/deliver", headers=PARENT).status_code == 404


# ---------- Padres · Niño ----------


def test_a_child_with_their_chart_and_history(client, bea):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    check(client, bea, item, 0)
    view = client.get(f"/api/overview/children/{bea['id']}", headers=PARENT).json()
    assert len(view["chart"]) == 14 and view["chart"][-1] == {"day": MONDAY.date().isoformat(), "stars": 1}
    assert view["movements"][0]["reason"] == "mission_completed"


def test_stars_can_be_taken_away_but_not_more_than_they_have(client, bea):
    client.post(f"/api/children/{bea['id']}/stars/gift", json={"stars": 5}, headers=PARENT)
    url = f"/api/children/{bea['id']}/stars/take"
    assert client.post(url, json={"stars": 2}, headers=PARENT).json() == {"stars": 3}
    assert client.post(url, json={"stars": 4}, headers=PARENT).status_code == 422
    assert client.post(url, json={"stars": 1}).status_code == 401
    assert descriptions(client, limit=1) == ["Quitaste estrellas a Bea · -2 estrellas"]


# ---------- Primeros pasos ----------


def test_first_steps_tell_what_is_ready(client):
    def setup():
        return client.get("/api/overview/setup", headers=PARENT).json()

    first = setup()
    assert (first["children"], first["switched_on"], first["code_changed"]) == (0, False, False)
    bea = create_child(client)
    mission(client, bea, "Despegue", steps=("Uno",))  # created and switched on for her, as the tests do
    ready = setup()
    assert ready["children"] == 1 and ready["missions"] == 1 and ready["switched_on"]
    client.put("/api/parents/code", json={"current_code": "1234", "code": "4321"}, headers=PARENT)
    assert client.get("/api/overview/setup", headers={"X-Parent-Code": "4321"}).json()["code_changed"]
