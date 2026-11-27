"""Rutinas de hoy, flexibles (rutinas-flexibles.html): a routine of today is there while some
child of its mission has not done it; one that rings at a time, by hand once it is over; who
did it already is greyed out; a race, once each a day; a parent takes someone out of it."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import PARENT
from tests.test_missions import create_child, put_in
from tests.test_routines import MONDAY, make_morning
from tests.test_routines_by_hand import start
from tests.test_routines_race import kids, race  # noqa: F401 (fixtures)
from tests.test_settings import FixedClock
from tests.test_today import mark


@pytest.fixture
def clock():
    return FixedClock(MONDAY)


@pytest.fixture
def client(data_dir, clock):
    with TestClient(create_app(data_dir, clock=clock)) as c:
        yield c


def by_hand(client, timed=True):
    return {r["name"]: r for r in client.get(f"/api/routines/by-hand?timed={str(timed).lower()}").json()}


def done_all(client, child, mission):
    for task in mission["tasks"]:
        mark(client, child, mission, task["id"])


@pytest.fixture
def morning(client):
    """Despegue (rings at 6:30, goal 7:30) for Bea and Alex; Noa in the mission, not in the routine."""
    bea, alex = create_child(client), create_child(client, name="Alex", preset="dinosaur")
    noa = create_child(client, name="Noa", preset="fox")
    routine = make_morning(client, kids=[bea["id"], alex["id"]])
    put_in(client, routine["mission_id"], noa)
    client.put(f"/api/routines/{routine['id']}/kids", json={"kids": [bea["id"], alex["id"]]}, headers=PARENT)
    mission = client.get(f"/api/missions/{routine['mission_id']}").json()
    return {"routine": routine, "mission": mission, "bea": bea, "alex": alex, "noa": noa}


def test_one_at_a_time_by_hand_only_once_over_and_for_who_is_left(client, clock, morning):
    assert "Despegue" not in by_hand(client)  # 7:02: it is ringing
    done_all(client, morning["bea"], morning["mission"])
    clock.moment = MONDAY.replace(hour=8)
    assert "Despegue" not in by_hand(client, timed=False)  # the children's ⏰: only the ones by hand
    found = by_hand(client)["Despegue"]
    assert [(k["name"], k["done"], k["chosen"]) for k in found["kids"]] == [
        ("Bea", True, False),
        ("Alex", False, True),
        ("Noa", False, False),
    ]
    routine_id = morning["routine"]["id"]
    assert start(client, {"id": routine_id}, [morning["bea"]["id"]]).status_code == 422  # she did it
    assert start(client, {"id": routine_id}, [morning["noa"]["id"]]).status_code == 204
    current = client.get("/api/routines/current").json()
    assert current["manual"] is True and [p["child"]["name"] for p in current["people"]] == ["Noa"]
    assert current["parts"][0]["minutes"] == 10  # its minutes, one part after the other


def test_by_hand_once_finished_and_it_ends_for_today_but_stays_for_the_others(client, clock, morning):
    client.post(f"/api/routines/{morning['routine']['id']}/finish", headers=PARENT)  # 7:02, finished early
    assert "Despegue" in by_hand(client)
    start(client, {"id": morning["routine"]["id"]}, [morning["alex"]["id"]])
    assert client.get("/api/routines/current").json()["manual"] is True  # not ringing again at its time
    client.post(f"/api/routines/{morning['routine']['id']}/notes", json={"kind": "ended"})
    assert client.get("/api/routines/current").json() is None
    assert "Despegue" in by_hand(client)  # nobody has done the mission yet


def test_when_everyone_did_it_it_is_no_longer_there(client, clock, morning):
    clock.moment = MONDAY.replace(hour=8)
    for kid in ("bea", "alex", "noa"):
        done_all(client, morning[kid], morning["mission"])
    assert "Despegue" not in by_hand(client)


def test_a_race_once_each_a_day(client, clock, kids, race):  # noqa: F811 (fixtures)
    bea, alex = kids
    start(client, race, [bea["id"]])
    clock.moment = clock.moment + timedelta(minutes=30)  # lost: the time is up
    client.post(f"/api/routines/{race['id']}/race/end")
    found = by_hand(client, timed=False)["Tarde"]
    assert [(k["name"], k["done"]) for k in found["kids"]] == [("Bea", True), ("Alex", False)]
    assert start(client, race, [bea["id"]]).status_code == 422
    again = client.get("/api/routines/races/again", headers=PARENT).json()
    assert again == []  # someone can still race it: no need to start it again


def test_a_parent_takes_someone_out_and_puts_them_back(client, morning):
    url = f"/api/routines/{morning['routine']['id']}/who"
    who = client.get(url, headers=PARENT).json()
    assert [(k["name"], k["here"]) for k in who] == [("Bea", True), ("Alex", True), ("Noa", False)]
    client.put(url, json={"kids": [morning["bea"]["id"]]}, headers=PARENT)
    assert [p["child"]["name"] for p in client.get("/api/routines/current").json()["people"]] == ["Bea"]
    client.put(url, json={"kids": [morning["bea"]["id"], morning["alex"]["id"]]}, headers=PARENT)
    assert len(client.get("/api/routines/current").json()["people"]) == 2
    assert client.put(url, json={"kids": ["nope"]}, headers=PARENT).status_code == 422
    assert client.put(url, json={"kids": []}, headers=PARENT).status_code == 204  # nobody: finished
    assert client.get("/api/routines/current").json() is None
