from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import PARENT
from tests.test_missions import add_step, create_child, create_mission
from tests.test_settings import FixedClock
from tests.test_today import check, descriptions

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
    """"Aterrizaje": started by hand, two parts of 3 and 4 minutes."""
    routine = client.post("/api/routines", json={"name": "Aterrizaje", "wake": "16:00"}, headers=PARENT).json()
    url = f"/api/routines/{routine['id']}"
    client.patch(url, json={"wake": None}, headers=PARENT)
    client.patch(f"{url}/parts/{routine['parts'][0]['id']}", json={"name": "guardar las cosas", "minutes": 3},
                 headers=PARENT)
    client.post(f"{url}/parts", json={"name": "lavarse las manos"}, headers=PARENT)
    second = client.get(url).json()["parts"][1]
    client.patch(f"{url}/parts/{second['id']}", json={"minutes": 4}, headers=PARENT)
    return client.get(url).json()


def start(client, routine, kids):
    return client.post(f"/api/routines/{routine['id']}/start", json={"kids": kids})


def test_a_routine_by_hand_has_no_times_of_its_own(client, landing):
    assert landing["manual"] is True and landing["wake"] is None and landing["goal"] is None
    assert [(p["at"], p["start"], p["end"]) for p in landing["parts"]] == [(None, "00:00", "00:03"),
                                                                          (None, "00:03", "00:07")]
    assert landing["minutes"] == 7
    url = f"/api/routines/{landing['id']}"
    assert client.patch(url, json={"goal": {"at": "18:00"}}, headers=PARENT).status_code == 422
    # Back to a time: the first part five minutes after it rings
    back = client.patch(url, json={"wake": "18:00"}, headers=PARENT).json()
    assert back["manual"] is False and back["parts"][0]["start"] == "18:05"


def test_started_by_hand_with_who_has_come_home(client, landing, clock):
    bea, alex = create_child(client), create_child(client, name="Alex", preset="dinosaur")
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


def test_each_child_with_their_mission(client, landing):
    bea = create_child(client)
    mission = create_mission(client, bea["id"], name="Aterrizaje").json()
    add_step(client, mission["id"], "Zapatos")
    client.put(f"/api/routines/{landing['id']}/missions/{bea['id']}", json={"mission_id": mission["id"]},
               headers=PARENT)
    start(client, landing, [bea["id"]])
    mission = client.get(f"/api/missions/{mission['id']}").json()
    check(client, bea, mission, 0)
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
