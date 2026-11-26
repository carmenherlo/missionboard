"""The race, more fun (carrera-divertida.html, 26/11): it goes by the times of each
«¡Hecho!»; a «con cuidado» task in the middle is a pit stop (the race stands still), the
ones after the last raced task are the landing, past the flag; a task done faster than the
alien is a turbo; the judges send tasks to be done again instead of taking stars away."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage import db
from tests.conftest import PARENT
from tests.test_missions import add_task, create_child, create_mission
from tests.test_routines_by_hand import MONDAY, start
from tests.test_settings import FixedClock
from tests.test_today import descriptions, mark

GO = 0.1  # «3, 2, 1, ¡YA!»: the race starts 6 seconds after it is launched


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


def make_race(client, *tasks):
    """A race by hand with these tasks: (text, minutes, careful minutes or None)."""
    mission = create_mission(client, name="Alunizaje").json()
    for text, _, _ in tasks:
        created = add_task(client, mission["id"], text).json()["tasks"]
    routine = client.post("/api/routines", json={"mission_id": mission["id"], "wake": "16:00"}, headers=PARENT).json()
    url = f"/api/routines/{routine['id']}"
    client.patch(url, json={"wake": None}, headers=PARENT)
    for task, (_, minutes, careful) in zip(created, tasks, strict=True):
        client.patch(f"{url}/parts/{task['id']}", json={"minutes": minutes}, headers=PARENT)
        if careful:
            client.put(f"{url}/parts/{task['id']}/slow", json={"minutes": careful}, headers=PARENT)
    client.put(f"{url}/race", json={"on_time": 1}, headers=PARENT)
    return {"id": routine["id"], "mission": mission, "tasks": [t["id"] for t in created]}


def done_at(client, race, kids, clock, task, minutes):
    clock.moment = MONDAY + timedelta(minutes=minutes)
    for kid in kids:
        mark(client, kid, race["mission"], task)


def race_now(client):
    return client.get("/api/routines/current").json()


@pytest.fixture
def despegue(client):
    """Vestirse 10 · Dientes 5 (con cuidado, 2) · Abrigo 10: the teeth are a pit stop."""
    return make_race(client, ("Vestirse", 10, None), ("Dientes", 5, 2), ("Abrigo", 10, None))


@pytest.fixture
def alunizaje(client):
    """Cena 10 · Ropa 10 · Dientes 5 (con cuidado, 2): the teeth are the landing."""
    return make_race(client, ("Cena", 10, None), ("Ropa", 10, None), ("Dientes", 5, 2))


def test_the_race_lasts_only_its_raced_tasks(client, kids, despegue):
    start(client, despegue, [k["id"] for k in kids])
    assert race_now(client)["race"]["minutes"] == 20  # not 25: the teeth do not count


def test_a_pit_stop_stands_the_race_still(client, kids, despegue, clock):
    dress, teeth, coat = despegue["tasks"]
    start(client, despegue, [k["id"] for k in kids])
    done_at(client, despegue, kids, clock, dress, GO + 9.5)
    clock.moment = MONDAY + timedelta(minutes=GO + 12.5)  # 3 minutes in the pit stop
    assert race_now(client)["race"]["boxes"] == pytest.approx(3)
    done_at(client, despegue, kids, clock, teeth, GO + 14.5)  # 5 minutes there
    # 20 minutes of race: without the pit stop, it would be lost by now
    clock.moment = MONDAY + timedelta(minutes=GO + 22)
    assert race_now(client)["race"]["boxes"] == pytest.approx(5)
    done_at(client, despegue, kids, clock, coat, GO + 24)
    ended = client.post(f"/api/routines/{despegue['id']}/race/end").json()
    assert ended["took_seconds"] == 19 * 60  # 24 minutes, 5 of them in the pit stop
    assert [(t["name"], t["seconds"], t["careful"]) for t in ended["tasks"]] == [
        ("Vestirse", 570, False),
        ("Dientes", 300, True),
        ("Abrigo", 570, False),
    ]
    assert race_now(client) is None  # nothing left: the routine is over


def test_in_a_pit_stop_the_time_does_not_run_out(client, kids, despegue, clock):
    dress = despegue["tasks"][0]
    start(client, despegue, [k["id"] for k in kids])
    done_at(client, despegue, kids, clock, dress, GO + 9)
    clock.moment = MONDAY + timedelta(minutes=GO + 40)  # still brushing: no race time goes by
    assert race_now(client) is not None


def test_after_the_flag_comes_the_landing(client, kids, alunizaje, clock):
    dinner, clothes, teeth = alunizaje["tasks"]
    start(client, alunizaje, [k["id"] for k in kids])
    assert client.post(f"/api/routines/{alunizaje['id']}/race/end").status_code == 409  # still racing
    done_at(client, alunizaje, kids, clock, dinner, GO + 9.5)
    done_at(client, alunizaje, kids, clock, clothes, GO + 19)
    ended = client.post(f"/api/routines/{alunizaje['id']}/race/end").json()
    assert ended["took_seconds"] == 19 * 60 and ended["outcome"] == "slow"  # the alien got there at 18
    again = client.post(f"/api/routines/{alunizaje['id']}/race/end").json()
    assert again["id"] == ended["id"]  # another tablet, a reload: the same result
    current = race_now(client)
    assert current["race"]["result"]["id"] == ended["id"]  # the landing goes on
    clock.moment = MONDAY + timedelta(minutes=GO + 33)  # past the flag: still landing
    assert race_now(client) is not None
    clock.moment = MONDAY + timedelta(minutes=GO + 19 + 5 + 10)  # its minutes and 10 more: over
    assert race_now(client) is None


def test_a_task_faster_than_the_alien_is_a_turbo(client, kids, alunizaje, clock):
    dinner, clothes, _ = alunizaje["tasks"]
    start(client, alunizaje, [k["id"] for k in kids])
    done_at(client, alunizaje, kids, clock, dinner, GO + 8)  # the alien takes 9 there: turbo
    assert race_now(client)["race"]["turbos"] == [dinner]
    done_at(client, alunizaje, kids, clock, clothes, GO + 18.1)  # 10.1: no turbo
    ended = client.post(f"/api/routines/{alunizaje['id']}/race/end").json()
    assert ended["outcome"] == "won"  # 18:06 of race, but the alien lost 10 seconds: it got there at 18:10


def test_the_judges_send_a_task_to_be_done_again(client, kids, alunizaje, clock):
    dinner, clothes, teeth = alunizaje["tasks"]
    start(client, alunizaje, [k["id"] for k in kids])
    done_at(client, alunizaje, kids, clock, dinner, GO + 2)
    done_at(client, alunizaje, kids, clock, clothes, GO + 12)
    race = client.post(f"/api/routines/{alunizaje['id']}/race/end").json()
    assert race["given"] is None and race["stars"] == 1
    url = f"/api/routines/races/{race['id']}"
    assert client.post(f"{url}/redo", json={"tasks": [dinner]}).status_code == 401
    assert client.post(f"{url}/redo", json={"tasks": ["nope"]}, headers=PARENT).status_code == 404
    redo = client.post(f"{url}/redo", json={"tasks": [dinner]}, headers=PARENT).json()
    assert redo["redo"] == [dinner] and redo["given"] is None
    assert descriptions(client, limit=1) == ["Carrera «Alunizaje»: los jueces piden repasar · Cena"]
    assert client.post(f"{url}/review", json={"give": True}, headers=PARENT).status_code == 409  # first, done again
    assert [r["id"] for r in client.get("/api/routines/races/to-review", headers=PARENT).json()] == [race["id"]]
    before = client.get(f"/api/children/{kids[0]['id']}/stars", headers=PARENT).json()["stars"]
    fixed = client.post(f"{url}/fixed", headers=PARENT).json()
    assert fixed["given"] is True
    assert client.get(f"/api/children/{kids[0]['id']}/stars", headers=PARENT).json()["stars"] == before + 1
    assert client.post(f"{url}/fixed", headers=PARENT).status_code == 409


def test_the_voice_explains_each_new_thing_the_first_times(client, kids, alunizaje):
    start(client, alunizaje, [k["id"] for k in kids])
    url = f"/api/routines/{alunizaje['id']}/race/tips"
    assert client.post(url, json={"tip": "magic"}).status_code == 422
    for _ in range(2):
        assert client.post(url, json={"tip": "turbo"}).status_code == 204
    assert race_now(client)["race"]["tips"] == {"turbo": 2}


def test_the_marks_keep_when_they_were_done(client, kids, alunizaje, clock):
    start(client, alunizaje, [k["id"] for k in kids])
    done_at(client, alunizaje, kids, clock, alunizaje["tasks"][0], 3)
    mission = race_now(client)["people"][0]["mission"]
    assert mission["done_at"] == {alunizaje["tasks"][0]: "2026-11-02T17:03:10+01:00"}


def test_the_races_tasks_and_tips_come_with_a_migration(tmp_path):
    db.migrate(tmp_path, db.MIGRATIONS[:20])
    db.migrate(tmp_path)
    with db.connect(tmp_path) as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(races)")}
        assert {"tasks", "redo"} <= columns
        assert conn.execute("SELECT count(*) FROM race_tips").fetchone()[0] == 0


def test_a_parent_starts_a_race_again_the_same_day(client, kids, alunizaje, clock):
    dinner, clothes, teeth = alunizaje["tasks"]
    ids = [k["id"] for k in kids]
    start(client, alunizaje, ids)
    clock.moment = MONDAY + timedelta(minutes=GO + 25)  # started by mistake: lost
    assert race_now(client) is None
    assert client.get("/api/routines/by-hand").json() == []  # the children's ⏰: once a day
    assert start(client, alunizaje, ids).status_code == 404
    url = f"/api/routines/{alunizaje['id']}/start-again"
    assert client.post(url, json={"kids": ids}).status_code == 401
    assert [r["id"] for r in client.get("/api/routines/races/again", headers=PARENT).json()] == [alunizaje["id"]]
    for kid in kids:  # the mission goes on after a lost race: undone, as if again
        for task in alunizaje["tasks"]:
            mark(client, kid, alunizaje["mission"], task, checked=False)
    assert client.post(url, json={"kids": ids}, headers=PARENT).status_code == 204
    assert race_now(client)["race"]["result"] is None  # not the race lost before
    done_at(client, alunizaje, kids, clock, dinner, GO + 25 + 5)
    done_at(client, alunizaje, kids, clock, clothes, GO + 25 + 12)
    ended = client.post(f"/api/routines/{alunizaje['id']}/race/end").json()
    assert ended["outcome"] == "won" and ended["took_seconds"] == 12 * 60 - 6
