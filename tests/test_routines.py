from datetime import datetime, timedelta, timezone

import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage.config_migrations import CURRENT_VERSION
from app.storage.config_store import config_path
from tests.conftest import PARENT
from tests.test_missions import add_step, add_task, create_child, create_mission, patch
from tests.test_settings import FixedClock
from tests.test_today import descriptions, mark, set_active

MADRID = timezone(timedelta(hours=1))
MONDAY = datetime(2026, 11, 2, 7, 2, 30, tzinfo=MADRID)  # the morning routine, in "aseo"
PARTS = [("Preparar el desayuno", 10), ("Desayuno", 15), ("Aseo", 5), ("Vestirse", 5), ("Mochila", 10), ("Salir", 5)]


def make_morning(client, kids=None):
    """Despegue and its routine: rings at 6:30, its parts from 6:35 to 7:25, and the goal
    at 7:30, after 5 minutes of checking the missions. Monday to Friday."""
    mission = create_mission(client, name="Despegue", image="fluent/rocket").json()
    patch(client, mission["id"], days=["mon", "tue", "wed", "thu", "fri"])
    for text, _ in PARTS:
        tasks = add_task(client, mission["id"], text).json()["tasks"]
    add_step(client, mission["id"], tasks[2]["id"], "Dientes")
    add_step(client, mission["id"], tasks[2]["id"], "Cara")
    routine = client.post("/api/routines", json={"mission_id": mission["id"], "wake": "06:30"}, headers=PARENT).json()
    url = f"/api/routines/{routine['id']}"
    for part, (_, minutes) in zip(routine["parts"], PARTS):
        client.patch(f"{url}/parts/{part['id']}", json={"minutes": minutes}, headers=PARENT)
    client.patch(url, json={"goal": {"at": "07:30", "say": "¡Es hora de irse al cole!", "check_minutes": 5}}, headers=PARENT)
    if kids:
        client.put(f"{url}/kids", json={"kids": kids}, headers=PARENT)
    return client.get(url).json()


@pytest.fixture
def clock():
    return FixedClock(MONDAY)


@pytest.fixture
def client(data_dir, clock):
    with TestClient(create_app(data_dir, clock=clock)) as c:
        yield c


@pytest.fixture
def morning(client):
    return make_morning(client)


def current(client):
    return client.get("/api/routines/current").json()


def note(client, routine, kind, **body):
    return client.post(f"/api/routines/{routine['id']}/notes", json={"kind": kind, **body})


# ---------- which routine, when ----------


def test_its_parts_are_the_missions_tasks(client, morning):
    routine = current(client)
    assert routine["name"] == "Despegue" and routine["wake"] == "06:30"
    assert routine["mission_id"] == morning["mission_id"]
    assert routine["now"] == pytest.approx(7 * 60 + 2.5)
    assert [(p["text"], p["name"], p["start"], p["end"]) for p in routine["parts"]][:3] == [
        ("Preparar el desayuno", "preparar el desayuno", "06:35", "06:45"),
        ("Desayuno", "desayuno", "06:45", "07:00"),
        ("Aseo", "aseo", "07:00", "07:05"),
    ]
    assert routine["goal"]["check_minutes"] == 5 and routine["goal"]["at"] == "07:30"
    assert [s["text"] for s in routine["parts"][2]["steps"]] == ["Dientes", "Cara"]


def test_the_routine_follows_the_mission(client, morning):
    url = f"/api/missions/{morning['mission_id']}"
    tasks = client.get(url).json()["tasks"]
    # A new task: at the end, 5 minutes; a task renamed, or moved
    add_task(client, morning["mission_id"], "Abrigo")
    client.patch(f"{url}/tasks/{tasks[0]['id']}", json={"text": "El desayuno listo"}, headers=PARENT)
    order = [t["id"] for t in client.get(url).json()["tasks"]]
    order[1], order[2] = order[2], order[1]
    client.put(f"{url}/tasks/order", json={"ids": order}, headers=PARENT)
    routine = current(client)
    assert [p["text"] for p in routine["parts"]] == [
        "El desayuno listo", "Aseo", "Desayuno", "Vestirse", "Mochila", "Salir", "Abrigo"]
    assert routine["parts"][1]["start"] == "06:45" and routine["parts"][1]["end"] == "06:50"  # its minutes go with it
    assert routine["goal"]["at"] == "07:35"  # it starts at a time: the end follows
    # A task deleted: out of the routine; the first one's time stays
    client.delete(f"{url}/tasks/{tasks[0]['id']}", headers=PARENT)
    routine = current(client)
    assert routine["parts"][0]["text"] == "Aseo" and routine["parts"][0]["start"] == "06:35"


def test_a_mission_deleted_takes_its_routine(client, morning):
    client.delete(f"/api/missions/{morning['mission_id']}", headers=PARENT)
    assert client.get("/api/routines").json() == []


def test_a_routine_needs_a_task_and_is_one_per_mission(client, morning):
    url = f"/api/missions/{morning['mission_id']}/tasks"
    tasks = client.get(f"/api/missions/{morning['mission_id']}").json()["tasks"]
    for task in tasks[1:]:
        assert client.delete(f"{url}/{task['id']}", headers=PARENT).status_code == 200
    assert client.delete(f"{url}/{tasks[0]['id']}", headers=PARENT).status_code == 409
    body = {"mission_id": morning["mission_id"], "wake": "09:00"}
    assert client.post("/api/routines", json=body, headers=PARENT).status_code == 409
    empty = create_mission(client, name="Vacía").json()
    assert client.post("/api/routines", json={"mission_id": empty["id"], "wake": "09:00"}, headers=PARENT).status_code == 422
    assert client.post("/api/routines", json={"mission_id": "nope", "wake": "09:00"}, headers=PARENT).status_code == 404


def test_a_task_that_would_break_its_routine_is_refused(client, clock):
    mission = create_mission(client, name="Muy pronto").json()
    add_task(client, mission["id"], "Una")
    client.post("/api/routines", json={"mission_id": mission["id"], "ends": "00:12"}, headers=PARENT)
    add_task(client, mission["id"], "Dos")
    assert add_task(client, mission["id"], "Tres").status_code == 422  # it would start the day before
    assert len(client.get(f"/api/missions/{mission['id']}").json()["tasks"]) == 2


def test_a_task_that_would_make_two_routines_ring_together_is_refused(client, morning):
    other = create_mission(client, name="Otra").json()
    add_task(client, other["id"], "Una")
    assert client.post("/api/routines", json={"mission_id": other["id"], "wake": "07:40"}, headers=PARENT).status_code == 201
    assert add_task(client, morning["mission_id"], "Más").status_code == 201  # until 7:35
    assert add_task(client, morning["mission_id"], "Más").status_code == 201  # until 7:40, just in time
    assert add_task(client, morning["mission_id"], "Más").status_code == 409  # until 7:45


def test_a_one_minute_warning_in_every_part_by_default(client, morning):
    url = f"/api/routines/{morning['id']}/parts/{morning['parts'][1]['id']}"
    client.patch(url, json={"warnings": [5, 1]}, headers=PARENT)
    warnings = [p["warnings"] for p in current(client)["parts"]]
    assert warnings == [[1], [5, 1], [1], [1], [1], [1]]


@pytest.mark.parametrize("moment, on", [
    (MONDAY.replace(hour=6, minute=29, second=59), False),
    (MONDAY.replace(hour=6, minute=30, second=0), True),
    (MONDAY.replace(hour=7, minute=29, second=59), True),
    (MONDAY.replace(hour=7, minute=30, second=0), False),
    (MONDAY.replace(day=7), False),  # Saturday
])
def test_it_is_on_from_its_wake_up_until_its_goal_on_its_days(client, morning, clock, moment, on):
    clock.moment = moment
    assert (current(client) is not None) == on


# ---------- who is in it, and their hours ----------


def test_only_its_children_with_something_on_and_the_goal_waits_for_them(client):
    bea, alex = create_child(client), create_child(client, name="Alex", preset="dinosaur")
    noa = create_child(client, name="Noa", preset="fox")
    morning = make_morning(client, kids=[bea["id"], alex["id"]])
    mission = client.get(f"/api/missions/{morning['mission_id']}").json()
    assert [p["child"]["name"] for p in current(client)["people"]] == ["Bea", "Alex"]
    assert all(noa["id"] != p["child"]["id"] for p in current(client)["people"])
    for task in mission["tasks"]:  # nothing on for Alex: not beside the clock
        set_active(client, mission, alex, task["id"], False)
        for step in task["steps"]:
            set_active(client, mission, alex, step["id"], False)
    people = current(client)["people"]
    assert [p["child"]["name"] for p in people] == ["Bea"]
    assert people[0]["mission"]["total"] == 7 and people[0]["mission"]["done"] == 0
    assert people[0]["mission"]["colors"]["color"] == mission["color"]
    for task in mission["tasks"]:
        for item in task["steps"] or [task]:
            mark(client, bea, mission, item["id"])
    assert current(client)["people"][0]["mission"]["completed"] is True


def test_a_task_off_for_everyone_still_counts_for_the_time_and_the_voice(client):
    bea = create_child(client)
    morning = make_morning(client)
    mission = client.get(f"/api/missions/{morning['mission_id']}").json()
    first = mission["tasks"][0]
    set_active(client, mission, bea, first["id"], False)
    routine = current(client)
    assert routine["parts"][0]["text"] == "Preparar el desayuno" and routine["parts"][0]["end"] == "06:45"
    day = client.get(f"/api/children/{bea['id']}/today").json()
    assert first["text"] not in [t["text"] for t in day["missions"][0]["tasks"]]


def test_two_schedules_the_routines_for_its_children_and_the_missions_for_the_rest(client, clock):
    bea, noa = create_child(client), create_child(client, name="Noa", preset="fox")
    morning = make_morning(client, kids=[bea["id"]])
    patch(client, morning["mission_id"], schedule={"start": "07:00", "end": "09:00"})
    client.patch(f"/api/routines/{morning['id']}", json={"days": ["mon", "tue"]}, headers=PARENT)

    def state(child, moment):
        clock.moment = moment
        return client.get(f"/api/children/{child['id']}/today").json()["missions"][0]["state"]

    monday = MONDAY
    assert state(bea, monday.replace(hour=6, minute=40)) == "open"  # the routine's: 6:35 to 7:30
    assert state(noa, monday.replace(hour=6, minute=40)) == "upcoming"  # the mission's: 7:00 to 9:00
    assert state(bea, monday.replace(hour=8)) == "closed"
    assert state(noa, monday.replace(hour=8)) == "open"
    wednesday = monday.replace(day=4)  # not one of the routine's days: the mission's for everyone
    assert state(bea, wednesday.replace(hour=6, minute=40)) == "upcoming"
    assert state(bea, wednesday.replace(hour=8)) == "open"


def test_the_routines_days_are_within_the_missions(client, morning):
    url = f"/api/routines/{morning['id']}"
    assert client.patch(url, json={"days": ["sat"]}, headers=PARENT).status_code == 422
    # The mission loses a day: the routine too (and gets it back with it)
    patch(client, morning["mission_id"], days=["mon", "tue"])
    assert client.get(url).json()["days"] == ["mon", "tue"]
    patch(client, morning["mission_id"], days=["mon", "tue", "wed", "thu", "fri"])
    assert client.get(url).json()["days"] == ["mon", "tue", "wed", "thu", "fri"]


def test_a_task_not_that_day_and_the_routine_rearranges_itself(client, clock):
    mission = create_mission(client, name="Alunizaje").json()
    patch(client, mission["id"], days=["mon", "tue", "wed", "thu", "fri", "sun"])
    for text in ("Cena", "Ropa", "Dientes"):
        tasks = add_task(client, mission["id"], text).json()["tasks"]
    client.patch(f"/api/missions/{mission['id']}/tasks/{tasks[1]['id']}", json={"days": ["mon", "tue", "wed", "thu", "sun"]},
                 headers=PARENT)
    client.post("/api/routines", json={"mission_id": mission["id"], "ends": "19:30"}, headers=PARENT)
    clock.moment = datetime(2026, 11, 2, 19, 20, tzinfo=MADRID)  # Monday: 19:15 to 19:30
    on = current(client)
    assert [(p["text"], p["start"]) for p in on["parts"]] == [("Cena", "19:15"), ("Ropa", "19:20"), ("Dientes", "19:25")]
    clock.moment = datetime(2026, 11, 6, 19, 25, tzinfo=MADRID)  # Friday: without Ropa, it still ends at 19:30
    on = current(client)
    assert [(p["text"], p["start"]) for p in on["parts"]] == [("Cena", "19:20"), ("Dientes", "19:25")]
    assert on["ends"] == "19:30"
    clock.moment = datetime(2026, 11, 6, 19, 16, tzinfo=MADRID)  # before it starts that day
    assert current(client) is None


def test_a_routine_with_no_task_that_day_does_not_go(client, clock):
    mission = create_mission(client, name="Alunizaje").json()
    task = add_task(client, mission["id"], "Cena").json()["tasks"][0]
    client.patch(f"/api/missions/{mission['id']}/tasks/{task['id']}", json={"days": ["tue"]}, headers=PARENT)
    client.post("/api/routines", json={"mission_id": mission["id"], "starts": "19:00"}, headers=PARENT)
    clock.moment = datetime(2026, 11, 2, 19, 1, tzinfo=MADRID)  # Monday
    assert current(client) is None
    assert client.get("/api/routines/next").json()["in_days"] == 1  # Tuesday's
    clock.moment = datetime(2026, 11, 3, 19, 1, tzinfo=MADRID)
    assert current(client) is not None


def test_a_trial_on_any_day_with_what_they_have(client, clock, morning):
    bea = create_child(client)
    clock.moment = MONDAY.replace(day=7)  # Saturday: no mission today
    trial = client.get(f"/api/routines/{morning['id']}/trial", headers=PARENT).json()
    assert trial["trial"] is True
    person = trial["people"][0]
    assert person["child"]["id"] == bea["id"] and person["mission"]["total"] == 7 and len(person["mission"]["marks"]) == 7


# ---------- what the screen tells ----------


def test_rang_once_a_day_and_stopped(client, morning):
    assert note(client, morning, "started").status_code == 204
    note(client, morning, "started")  # the tablet reloaded
    note(client, morning, "stopped", seconds=42)
    assert current(client)["stopped"] is True
    assert descriptions(client, limit=2) == [  # "started" only once
        "Pararon la rutina «Despegue» · a los 42 s",
        "Sonó la rutina «Despegue»",
    ]


def test_parts_and_goal_go_to_the_log(client, morning):
    note(client, morning, "part", part=2)
    assert note(client, morning, "part", part=99).status_code == 404
    note(client, morning, "goal", early=True)
    assert descriptions(client, limit=2) == [
        "Rutina «Despegue»: llega la meta · antes de hora: todos habían firmado",
        "Rutina «Despegue»: empieza aseo",
    ]


def test_everyone_signed_early_it_is_over_for_today(client, morning):
    note(client, morning, "goal", early=False)
    assert current(client) is not None  # the goal at its time: it ends by itself
    note(client, morning, "goal", early=True)
    assert current(client) is None


def test_closed_until_its_next_part(client, morning):
    note(client, morning, "closed", phase="part-2")
    assert current(client)["closed_phase"] == "part-2"
    assert descriptions(client, limit=1) == ["Cerraron la rutina «Despegue»"]


def test_finished_for_the_day_by_a_parent(client, morning, clock):
    assert client.post(f"/api/routines/{morning['id']}/finish").status_code == 401
    assert client.post(f"/api/routines/{morning['id']}/finish", headers=PARENT).status_code == 204
    assert current(client) is None
    clock.moment = MONDAY.replace(day=3)  # Tuesday: it rings again
    assert current(client) is not None


def test_notes_only_for_the_routine_going_on(client, morning, clock):
    clock.moment = MONDAY.replace(hour=12)
    assert note(client, morning, "started").status_code == 409


# ---------- the routines in config.yaml ----------


@pytest.mark.parametrize("routine", [
    {"id": "r", "mission_id": "m", "wake": "07:00", "anchor": "end", "goal": {"at": "00:01"},
     "parts": [{"id": "t", "at": "07:00", "minutes": 10}]},  # it would start the day before
    {"id": "r", "mission_id": "m", "wake": "07:00", "goal": {"at": "07:05"},
     "offsets": {"mon": -500}, "parts": [{"id": "t", "at": "07:00", "minutes": 10}]},  # moved out of its day
])
def test_a_routine_whose_times_do_not_add_up_stops_the_app(data_dir, clock, routine):
    data_dir.mkdir(parents=True)
    mission = {"id": "m", "name": "M", "tasks": [{"id": "t", "text": "T"}]}
    doc = {"version": CURRENT_VERSION, "children": [], "missions": [mission], "prizes": [], "routines": [routine]}
    config_path(data_dir).write_text(yaml.safe_dump(doc))
    with pytest.raises(Exception):
        with TestClient(create_app(data_dir, clock=clock)):
            pass


def test_the_next_routine_to_ring(client, clock, morning):
    clock.moment = MONDAY.replace(hour=5, minute=0)
    assert client.get("/api/routines/next").json() | {"image_url": None} == {
        "id": morning["id"], "name": "Despegue", "at": "06:30", "in_days": 0, "image_url": None}
    clock.moment = MONDAY.replace(hour=9, minute=0)  # rung already today: tomorrow's
    assert client.get("/api/routines/next").json()["in_days"] == 1
    clock.moment = MONDAY.replace(day=6, hour=9)  # Friday after it: Monday's (no weekends)
    assert client.get("/api/routines/next").json()["in_days"] == 3
