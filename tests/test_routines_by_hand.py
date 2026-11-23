from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import PARENT
from tests.test_missions import add_task, create_child, create_mission, patch
from tests.test_settings import FixedClock
from tests.test_today import descriptions, mark

MADRID = timezone(timedelta(hours=1))
MONDAY = datetime(2026, 11, 2, 17, 0, 10, tzinfo=MADRID)


@pytest.fixture
def clock():
    return FixedClock(MONDAY)


@pytest.fixture
def client(data_dir, clock):
    with TestClient(create_app(data_dir, clock=clock)) as c:
        yield c


@pytest.fixture
def landing(client):
    """ "Aterrizaje": started by hand, two parts of 3 and 4 minutes."""
    mission = create_mission(client, name="Aterrizaje").json()
    add_task(client, mission["id"], "Guardar las cosas")
    tasks = add_task(client, mission["id"], "Lavarse las manos").json()["tasks"]
    routine = client.post("/api/routines", json={"mission_id": mission["id"], "wake": "16:00"}, headers=PARENT).json()
    url = f"/api/routines/{routine['id']}"
    client.patch(url, json={"wake": None}, headers=PARENT)
    client.patch(f"{url}/parts/{tasks[0]['id']}", json={"minutes": 3}, headers=PARENT)
    client.patch(f"{url}/parts/{tasks[1]['id']}", json={"minutes": 4}, headers=PARENT)
    return client.get(url).json()


def start(client, routine, kids):
    return client.post(f"/api/routines/{routine['id']}/start", json={"kids": kids})


def test_a_routine_by_hand_has_no_times_of_its_own(client, landing):
    assert landing["manual"] is True and landing["wake"] is None and landing["goal"] is None
    assert [(p["at"], p["start"], p["end"]) for p in landing["parts"]] == [
        (None, "00:00", "00:03"),
        (None, "00:03", "00:07"),
    ]
    assert landing["minutes"] == 7
    url = f"/api/routines/{landing['id']}"
    assert client.patch(url, json={"anchor": "end"}, headers=PARENT).status_code == 422
    # Back to a time: the first part five minutes after it rings
    back = client.patch(url, json={"wake": "18:00"}, headers=PARENT).json()
    assert back["manual"] is False and back["parts"][0]["start"] == "18:05"


def test_started_by_hand_with_who_has_come_home(client, landing, clock):
    bea = create_child(client)
    create_child(client, name="Alex", preset="dinosaur")
    assert client.get("/api/routines/current").json() is None
    by_hand = client.get("/api/routines/by-hand").json()
    assert [r["name"] for r in by_hand] == ["Aterrizaje"] and by_hand[0]["minutes"] == 7
    assert [k["name"] for k in by_hand[0]["kids"]] == ["Bea", "Alex"]
    assert start(client, landing, []).status_code == 422
    assert start(client, landing, [bea["id"]]).status_code == 204
    current = client.get("/api/routines/current").json()
    assert current["manual"] is True and current["started"] == pytest.approx(17 * 60 + 1 / 6)
    assert [p["start"] for p in current["parts"]] == ["17:00", "17:03"]
    assert [p["child"]["name"] for p in current["people"]] == ["Bea"]
    assert descriptions(client, limit=1) == ["Sonó la rutina «Aterrizaje»"]
    clock.moment = MONDAY + timedelta(minutes=7)  # its time is up
    assert client.get("/api/routines/current").json() is None


def test_it_ends_and_can_start_again(client, landing):
    bea = create_child(client)
    start(client, landing, [bea["id"]])
    assert client.post(f"/api/routines/{landing['id']}/notes", json={"kind": "ended", "early": True}).status_code == 204
    assert client.get("/api/routines/current").json() is None
    assert descriptions(client, limit=1) == ["Acabó la rutina «Aterrizaje» · antes de hora: todos habían firmado"]
    assert start(client, landing, [bea["id"]]).status_code == 204


def test_finished_for_everyone_it_does_not_come_back(client, landing):
    bea = create_child(client)
    start(client, landing, [bea["id"]])
    assert client.post(f"/api/routines/{landing['id']}/finish", headers=PARENT).status_code == 204
    assert client.get("/api/routines/current").json() is None
    assert start(client, landing, [bea["id"]]).status_code == 204
    assert client.get("/api/routines/current").json()["manual"] is True


def test_the_missions_hours_rule_until_it_is_started_by_hand(client, landing):
    bea, alex = create_child(client), create_child(client, name="Alex", preset="dinosaur")
    patch(client, landing["mission_id"], schedule={"start": "18:00", "end": "21:00"})  # it is 17:00
    mission = client.get(f"/api/missions/{landing['mission_id']}").json()

    def today(child):
        return client.get(f"/api/children/{child['id']}/today").json()["missions"][0]

    assert today(bea)["state"] == "upcoming" and today(bea)["schedule"] == {"start": "18:00", "end": "21:00"}
    start(client, landing, [bea["id"]])
    assert today(bea)["state"] == "open"  # started, it opens for who has come home, only today
    assert today(alex)["state"] == "upcoming"
    for task in mission["tasks"]:
        mark(client, bea, mission, task["id"])
    assert client.get("/api/routines/current").json()["people"][0]["mission"]["completed"] is True


def test_not_on_its_days_or_unknown(client, landing, clock):
    bea = create_child(client)
    assert start(client, {"id": "nope"}, [bea["id"]]).status_code == 404
    client.patch(f"/api/routines/{landing['id']}", json={"days": ["sat"]}, headers=PARENT)
    assert client.get("/api/routines/by-hand").json() == []
    assert start(client, landing, [bea["id"]]).status_code == 404


def test_trying_one_by_hand_starts_it_now(client, landing):
    create_child(client)
    trial = client.get(f"/api/routines/{landing['id']}/trial", headers=PARENT).json()
    assert trial["manual"] is True and trial["started"] == pytest.approx(17 * 60 + 1 / 6)
    assert trial["parts"][0]["start"] == "17:00" and len(trial["people"]) == 1


def test_it_never_overlaps_a_routine_with_a_time(client, landing):
    url = f"/api/routines/{landing['id']}"
    assert client.patch(url, json={"days": ["mon", "tue", "wed", "thu", "fri"]}, headers=PARENT).status_code == 200


def test_by_hand_it_can_have_its_goal_after_checking(client, landing, clock):
    bea = create_child(client)
    url = f"/api/routines/{landing['id']}"
    routine = client.patch(url, json={"goal": {"check_minutes": 5, "at": "10:00"}}, headers=PARENT).json()
    assert routine["manual"] is True and routine["goal"]["at"] is None and routine["minutes"] == 12
    start(client, landing, [bea["id"]])
    current = client.get("/api/routines/current").json()
    assert current["goal"]["at"] == "17:12" and current["goal"]["check_minutes"] == 5
    clock.moment = MONDAY + timedelta(minutes=11)  # checking the missions
    assert client.get("/api/routines/current").json() is not None
    clock.moment = MONDAY + timedelta(minutes=12)
    assert client.get("/api/routines/current").json() is None
    # With a time again, the goal gets its own; and by hand once more, it keeps its checking
    timed = client.patch(url, json={"wake": "18:00"}, headers=PARENT).json()
    assert timed["goal"]["at"] == "18:17"  # its first part five minutes after it rings
    again = client.patch(url, json={"wake": None}, headers=PARENT).json()
    assert again["goal"] == {**timed["goal"], "at": None}


def test_a_parent_pauses_it_and_it_goes_on_where_it_was(client, landing, clock):
    bea = create_child(client)
    url = f"/api/routines/{landing['id']}/paused"
    assert client.put(url, json={"paused": True}, headers=PARENT).status_code == 409  # not on
    start(client, landing, [bea["id"]])
    assert client.put(url, json={"paused": True}).status_code == 401
    clock.moment = MONDAY + timedelta(minutes=2)
    assert client.put(url, json={"paused": True}, headers=PARENT).status_code == 204
    clock.moment = MONDAY + timedelta(minutes=30)  # long after its time: still there, still
    current = client.get("/api/routines/current").json()
    assert current["paused"] is True and current["now"] == pytest.approx(17 * 60 + 2 + 1 / 6)
    assert client.put(url, json={"paused": False}, headers=PARENT).status_code == 204
    current = client.get("/api/routines/current").json()
    assert current["paused"] is False and current["started"] == pytest.approx(17 * 60 + 28 + 1 / 6)
    assert current["now"] - current["started"] == pytest.approx(2)
    assert descriptions(client, limit=2) == [
        "La rutina «Aterrizaje» siguió tras la pausa",
        "Pausaron la rutina «Aterrizaje»",
    ]
