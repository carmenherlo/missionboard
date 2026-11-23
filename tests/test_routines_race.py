"""Modo carrera (modo-carrera.html): a routine started by hand whose parts end when every
child who has their task has done it, against a ghost; and «± Tiempo»."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import PARENT
from tests.test_missions import add_task, create_child, create_mission, patch
from tests.test_routines_by_hand import MONDAY, start
from tests.test_settings import FixedClock
from tests.test_today import descriptions, mark, set_active


@pytest.fixture
def clock():
    return FixedClock(MONDAY)


@pytest.fixture
def client(data_dir, clock):
    with TestClient(create_app(data_dir, clock=clock)) as c:
        yield c


@pytest.fixture
def kids(client):
    return create_child(client), create_child(client, name="Alex", preset="dinosaur")


@pytest.fixture
def race(client, kids):
    """ "Tarde", by hand, as a race: homework 10 minutes and shower 10 (the flag at 20, the
    ghost at 18, "muy rápido" up to 16). Alex has no homework."""
    mission = create_mission(client, name="Tarde").json()
    add_task(client, mission["id"], "Deberes")
    tasks = add_task(client, mission["id"], "Ducha").json()["tasks"]
    mission = client.get(f"/api/missions/{mission['id']}").json()
    set_active(client, mission, kids[1], tasks[0]["id"], False)
    routine = client.post("/api/routines", json={"mission_id": mission["id"], "wake": "16:00"}, headers=PARENT).json()
    url = f"/api/routines/{routine['id']}"
    client.patch(url, json={"wake": None}, headers=PARENT)
    for task in tasks:
        client.patch(f"{url}/parts/{task['id']}", json={"minutes": 10}, headers=PARENT)
    assert client.put(f"{url}/race", json={"on_time": 1, "fast": 2}, headers=PARENT).status_code == 200
    return {**client.get(url).json(), "mission": mission, "tasks": tasks}


def run(client, race, kids, clock, minutes):
    """Start it with both, everyone does everything, and `minutes` later it ends."""
    start(client, race, [k["id"] for k in kids])
    for task in race["tasks"]:
        for kid in kids:
            mark(client, kid, race["mission"], task["id"])
    clock.moment = MONDAY + timedelta(minutes=minutes)
    return client.post(f"/api/routines/{race['id']}/race/end")


def balance(client, kid):
    return client.get(f"/api/children/{kid['id']}/stars", headers=PARENT).json()["stars"]


def test_a_race_is_set_in_the_editor_and_only_by_hand(client, race):
    assert race["race"] == {"on_time": 1, "fast": 2, "review": True}
    url = f"/api/routines/{race['id']}"
    slow = client.put(f"{url}/parts/{race['tasks'][1]['id']}/slow", json={"minutes": 4}, headers=PARENT)
    assert [p["slow_minutes"] for p in slow.json()["parts"]] == [None, 4]
    assert client.put(f"{url}/race", json=None, headers=PARENT).json()["race"] is None
    client.patch(url, json={"wake": "18:00"}, headers=PARENT)
    assert client.put(f"{url}/race", json={}, headers=PARENT).status_code == 409
    assert client.put(f"{url}/race", json={}).status_code == 401


def test_the_screen_gets_its_rules_and_who_has_each_task(client, race, kids):
    start(client, race, [k["id"] for k in kids])
    current = client.get("/api/routines/current").json()
    assert current["race"] == {
        "on_time": 1,
        "fast": 2,
        "review": True,
        "minutes": 20,
        "ghost": 18,
        "fast_minutes": 16,
    }
    homework, shower = (t["id"] for t in race["tasks"])
    assert [p["mission"]["tasks"] for p in current["people"]] == [
        {homework: False, shower: False},
        {shower: False},
    ]
    mark(client, kids[0], race["mission"], homework)
    tasks = client.get("/api/routines/current").json()["people"][0]["mission"]["tasks"]
    assert tasks == {homework: True, shower: False}


def test_beating_the_ghost_waits_for_a_parent(client, race, kids, clock):
    ended = run(client, race, kids, clock, 17).json()
    assert (ended["outcome"], ended["stars"], ended["given"], ended["took_seconds"]) == ("won", 1, None, 17 * 60)
    assert client.get("/api/routines/current").json() is None
    stars_before = balance(client, kids[0])
    waiting = client.get("/api/routines/races/to-review", headers=PARENT).json()
    assert [r["id"] for r in waiting] == [ended["id"]]
    assert client.post(f"/api/routines/races/{ended['id']}/review", json={"give": True}).status_code == 401
    client.post(f"/api/routines/races/{ended['id']}/review", json={"give": True}, headers=PARENT)
    assert balance(client, kids[0]) == stars_before + 1
    assert client.get("/api/routines/races/to-review", headers=PARENT).json() == []
    review = client.post(f"/api/routines/races/{ended['id']}/review", json={"give": True}, headers=PARENT)
    assert review.status_code == 409
    assert descriptions(client, limit=1) == ["Revisaron la carrera «Tarde» · +1 ★"]


def test_very_fast_without_review_gives_them_at_once(client, race, kids, clock):
    client.put(f"/api/routines/{race['id']}/race", json={"on_time": 1, "fast": 2, "review": False}, headers=PARENT)
    before = [balance(client, k) for k in kids]
    ended = run(client, race, kids, clock, 15).json()
    assert (ended["outcome"], ended["stars"], ended["given"]) == ("fast", 2, True)
    assert [balance(client, k) for k in kids] == [b + 1 + 2 for b in before]  # the mission's star and the race's


def test_after_the_ghost_no_extra_stars(client, race, kids, clock):
    ended = run(client, race, kids, clock, 19).json()
    assert (ended["outcome"], ended["stars"]) == ("slow", 0)
    assert client.get("/api/routines/races/to-review", headers=PARENT).json() == []
    assert client.get("/api/routines/by-hand").json() == []  # a race, once a day


def test_it_cannot_end_while_someone_has_tasks_left(client, race, kids):
    start(client, race, [k["id"] for k in kids])
    assert client.post(f"/api/routines/{race['id']}/race/end").status_code == 409


def test_at_the_flag_it_is_lost_and_the_mission_closes(client, race, kids, clock):
    bea = kids[0]
    start(client, race, [k["id"] for k in kids])
    mark(client, bea, race["mission"], race["tasks"][0]["id"])
    clock.moment = MONDAY + timedelta(minutes=20)
    assert client.get("/api/routines/current").json() is None
    assert descriptions(client, limit=1) == ["Carrera «Tarde»: se acabó el tiempo"]
    day = client.get(f"/api/children/{bea['id']}/today").json()
    assert day["missions"][0]["state"] == "closed"
    assert mark(client, bea, race["mission"], race["tasks"][1]["id"]).status_code == 409
    # A parent can still open it today
    opened = client.post(f"/api/children/{bea['id']}/today/missions/{race['mission']['id']}/open", headers=PARENT)
    assert opened.json()["missions"][0]["state"] == "open"


def test_a_race_lost_closes_its_mission_even_if_starting_it_opened_it(client, race, kids, clock):
    bea = kids[0]
    patch(client, race["mission"]["id"], schedule={"start": "18:00", "end": "21:00"})  # it is 17:00: upcoming
    start(client, race, [k["id"] for k in kids])  # starting it by hand opens the mission today
    clock.moment = MONDAY + timedelta(minutes=20)
    client.get("/api/routines/current")  # the flag: lost
    day = client.get(f"/api/children/{bea['id']}/today").json()
    assert day["missions"][0]["state"] == "closed"
    opened = client.post(f"/api/children/{bea['id']}/today/missions/{race['mission']['id']}/open", headers=PARENT)
    assert opened.json()["missions"][0]["state"] == "open"  # a parent opening it afterwards wins


def test_a_parent_adds_minutes_to_a_part_only_today(client, race, kids, clock):
    start(client, race, [k["id"] for k in kids])
    url = f"/api/routines/{race['id']}/extra"
    shower = race["tasks"][1]["id"]
    assert client.post(url, json={"part_id": shower, "minutes": 5}).status_code == 401
    assert client.post(url, json={"part_id": shower, "minutes": 5}, headers=PARENT).json() == {"minutes": 15}
    current = client.get("/api/routines/current").json()
    assert current["extra"] == {shower: 5} and current["race"]["minutes"] == 25
    assert client.post(url, json={"part_id": shower, "minutes": -60}, headers=PARENT).json() == {"minutes": 1}
    assert descriptions(client, limit=1) == ["Rutina «Tarde»: Ducha -14 min"]
    assert client.get(f"/api/routines/{race['id']}").json()["parts"][1]["minutes"] == 10  # the routine, as it was


def test_by_the_clock_the_part_going_on_cannot_end_before_now(client, race, kids, clock):
    client.put(f"/api/routines/{race['id']}/race", json=None, headers=PARENT)
    start(client, race, [k["id"] for k in kids])
    url = f"/api/routines/{race['id']}/extra"
    homework, shower = (t["id"] for t in race["tasks"])
    clock.moment = MONDAY + timedelta(minutes=6, seconds=30)
    assert client.post(url, json={"part_id": homework, "minutes": -9}, headers=PARENT).json() == {"minutes": 7}
    assert [p["end"] for p in client.get("/api/routines/current").json()["parts"]][-1] == "17:17"
    clock.moment = MONDAY + timedelta(minutes=8)
    assert client.post(url, json={"part_id": homework, "minutes": 1}, headers=PARENT).status_code == 409  # over
    assert client.post(url, json={"part_id": shower, "minutes": 2}, headers=PARENT).json() == {"minutes": 12}
