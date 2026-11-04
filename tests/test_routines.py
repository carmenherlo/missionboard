from datetime import datetime, timedelta, timezone

import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage.config_store import config_path
from tests.conftest import PARENT
from tests.test_missions import add_step, create_child, create_mission
from tests.test_settings import FixedClock
from tests.test_today import check, descriptions

MADRID = timezone(timedelta(hours=1))
MONDAY = datetime(2026, 11, 2, 7, 2, 30, tzinfo=MADRID)  # the morning routine, in "el aseo"


@pytest.fixture
def clock():
    return FixedClock(MONDAY)


@pytest.fixture
def client(data_dir, clock):
    with TestClient(create_app(data_dir, clock=clock)) as c:
        yield c


def current(client):
    return client.get("/api/routines/current").json()


def note(client, kind, **body):
    return client.post("/api/routines/manana/notes", json={"kind": kind, **body})


# ---------- which routine, when ----------


def test_the_morning_routine_comes_with_the_migration(client):
    routine = current(client)
    assert routine["name"] == "Mañana" and routine["wake"] == "06:30"
    assert routine["now"] == pytest.approx(7 * 60 + 2.5)
    assert [(p["name"], p["start"], p["end"]) for p in routine["parts"]][:3] == [
        ("la preparación del desayuno", "06:35", "06:45"),
        ("el desayuno", "06:45", "07:00"),
        ("el aseo", "07:00", "07:05"),
    ]
    assert routine["parts"][-1]["name"] == "prepararse para salir"  # "firmar" became the goal's checking
    assert routine["goal"]["check_minutes"] == 5
    assert routine["goal"]["check_say"] == "No olvidéis firmar vuestras tareas antes de iros."
    assert routine["goal"]["at"] == "07:45" and routine["goal"]["say"] == "¡Es hora de irse al cole!"
    assert routine["parts"][2]["tasks"] == ["Lavarse los dientes", "Lavarse la cara"]
    assert routine["parts"][2]["image_url"].endswith("/toothbrush.svg")


def test_a_one_minute_warning_in_every_part_by_default(client):
    warnings = [p["warnings"] for p in current(client)["parts"]]
    assert warnings == [[1], [5, 1], [1], [1], [1], [1]]


@pytest.mark.parametrize("moment, on", [
    (MONDAY.replace(hour=6, minute=29, second=59), False),
    (MONDAY.replace(hour=6, minute=30, second=0), True),
    (MONDAY.replace(hour=7, minute=44, second=59), True),
    (MONDAY.replace(hour=7, minute=45, second=0), False),
    (MONDAY.replace(day=7), False),  # Saturday
])
def test_it_is_on_from_its_wake_up_until_its_goal_on_its_days(client, clock, moment, on):
    clock.moment = moment
    assert (current(client) is not None) == on


def test_each_child_with_their_mission_of_the_routine(client):
    bea = create_child(client)
    alex = create_child(client, name="Alex", preset="dinosaur")
    despegue = create_mission(client, bea["id"], name="Despegue").json()
    for text in ("Vestirse", "Desayunar"):
        add_step(client, despegue["id"], text)
    despegue = client.get(f"/api/missions/{despegue['id']}").json()
    client.put(f"/api/routines/manana/missions/{bea['id']}", json={"mission_id": despegue["id"]}, headers=PARENT)
    check(client, bea, despegue, 0)
    people = current(client)["people"]
    assert [p["child"]["name"] for p in people] == ["Bea", "Alex"]
    assert people[0]["mission"] == {
        "id": despegue["id"], "name": "Despegue", "done": 1, "total": 2, "completed": False,
    }
    assert people[0]["colors"]["color"] == bea["color"]
    assert people[1]["mission"] is None  # Alex has no mission in this routine
    check(client, bea, despegue, 1)
    assert current(client)["people"][0]["mission"]["completed"] is True


# ---------- what the screen tells ----------


def test_rang_once_a_day_and_stopped(client):
    assert note(client, "started").status_code == 204
    note(client, "started")  # the tablet reloaded
    note(client, "stopped", seconds=42)
    assert current(client)["stopped"] is True
    assert descriptions(client, limit=5) == [  # "started" only once
        "Pararon la rutina «Mañana» · a los 42 s",
        "Sonó la rutina «Mañana»",
    ]


def test_parts_and_goal_go_to_the_log(client):
    note(client, "part", part=2)
    assert note(client, "part", part=99).status_code == 404
    note(client, "goal", early=True)
    assert descriptions(client, limit=2) == [
        "Rutina «Mañana»: llega la meta · antes de hora: todos habían firmado",
        "Rutina «Mañana»: empieza el aseo",
    ]


def test_everyone_signed_early_it_is_over_for_today(client):
    note(client, "goal", early=False)
    assert current(client) is not None  # the goal at its time: it ends by itself
    note(client, "goal", early=True)
    assert current(client) is None


def test_closed_until_its_next_part(client):
    note(client, "closed", phase="part-2")
    assert current(client)["closed_phase"] == "part-2"
    assert descriptions(client, limit=1) == ["Cerraron la rutina «Mañana»"]


def test_finished_for_the_day_by_a_parent(client, clock):
    assert client.post("/api/routines/manana/finish").status_code == 401
    assert client.post("/api/routines/manana/finish", headers=PARENT).status_code == 204
    assert current(client) is None
    clock.moment = MONDAY.replace(day=3)  # Tuesday: it rings again
    assert current(client) is not None


def test_notes_only_for_the_routine_going_on(client, clock):
    clock.moment = MONDAY.replace(hour=12)
    assert note(client, "started").status_code == 409


# ---------- the routines in config.yaml ----------


def write_routines(data_dir, routines):
    data_dir.mkdir(parents=True)
    doc = {"version": 7, "children": [], "missions": [], "templates": [], "prizes": [], "routines": routines}
    config_path(data_dir).write_text(yaml.safe_dump(doc))


def test_only_the_routines_children(data_dir, clock):
    routine = {"id": "r", "name": "R", "wake": "07:00", "parts": [{"name": "algo", "at": "07:01", "minutes": 5}]}
    write_routines(data_dir, [routine])
    with TestClient(create_app(data_dir, clock=clock)) as client:
        bea = create_child(client)
        create_child(client, name="Alex", preset="dinosaur")
        doc = yaml.safe_load(config_path(data_dir).read_text())
        doc["routines"][0]["kids"] = [bea["id"]]
        config_path(data_dir).write_text(yaml.safe_dump(doc))
        assert [p["child"]["name"] for p in current(client)["people"]] == ["Bea"]


@pytest.mark.parametrize("routine", [
    {"id": "r", "name": "R", "wake": "07:00", "parts": [{"name": "a", "minutes": 5}]},  # first part, no time
    {"id": "r", "name": "R", "wake": "07:00", "parts": [
        {"name": "a", "at": "07:00", "minutes": 10}, {"name": "b", "at": "07:05", "minutes": 5}]},  # overlap
    {"id": "r", "name": "R", "wake": "07:00", "parts": [{"name": "a", "at": "07:00", "minutes": 10}],
     "goal": {"name": "g", "at": "07:05"}},  # goal before the end
])
def test_a_routine_whose_times_do_not_add_up_stops_the_app(data_dir, clock, routine):
    write_routines(data_dir, [routine])
    with pytest.raises(Exception):
        with TestClient(create_app(data_dir, clock=clock)):
            pass
