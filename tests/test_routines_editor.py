from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import PARENT
from tests.test_missions import add_task, create_child, create_mission, patch, saved
from tests.test_routines import PARTS, make_morning
from tests.test_settings import FixedClock
from tests.test_today import descriptions

MADRID = timezone(timedelta(hours=1))


@pytest.fixture
def clock():
    return FixedClock(datetime(2026, 11, 2, 16, 20, 30, tzinfo=MADRID))


@pytest.fixture
def client(data_dir, clock):
    with TestClient(create_app(data_dir, clock=clock)) as c:
        yield c


@pytest.fixture(autouse=True)
def morning(client):
    return make_morning(client)


def edit(client, method, path="", **body):
    url = f"/api/routines/{client.get('/api/routines').json()[0]['id']}"
    return client.request(method, f"{url}{path}", json=body or None, headers=PARENT)


def parts(routine):
    return [(p["text"], p["start"], p["end"]) for p in routine["parts"]]


def another_mission(client, name="Otra", tasks=("Una",)):
    mission = create_mission(client, name=name).json()
    for text in tasks:
        add_task(client, mission["id"], text)
    return mission


def create(client, mission, **times):
    return client.post("/api/routines", json={"mission_id": mission["id"], **times}, headers=PARENT)


# ---------- the list and a new routine ----------


def test_the_list_has_the_routines_with_their_missions_name_and_picture(client, morning):
    routines = client.get("/api/routines").json()
    assert [r["name"] for r in routines] == ["Despegue"]
    assert routines[0]["every_child"] is True and routines[0]["ends"] == "07:30"
    assert routines[0]["image_url"].endswith("rocket.svg")
    assert client.get(f"/api/missions/{morning['mission_id']}").json()["routine"]["id"] == morning["id"]


def test_a_new_routine_brings_every_task_with_five_minutes(client):
    mission = another_mission(client, "Deberes", ("Mates", "Lengua"))
    response = create(client, mission, wake="17:00")
    assert response.status_code == 201
    routine = response.json()
    assert routine["days"] == mission["days"]
    assert parts(routine) == [("Mates", "17:05", "17:10"), ("Lengua", "17:10", "17:15")]
    assert descriptions(client, limit=1) == ["Creaste la rutina «Deberes»"]


def test_stored_only_what_is_its_own(client, data_dir):
    entry = saved(data_dir)["routines"][0]
    assert "name" not in entry and "image" not in entry
    assert set(entry["parts"][0]) == {"id", "at", "minutes", "say", "spoken", "warnings"}


def test_two_routines_cannot_ring_at_the_same_time(client):
    assert create(client, another_mission(client), wake="07:00").status_code == 409
    weekend = another_mission(client, "Finde")
    patch(client, weekend["id"], days=["sat", "sun"])
    assert create(client, weekend, wake="07:00").status_code == 201  # on other days, fine


def test_changes_need_the_parent_code(client, morning):
    url = f"/api/routines/{morning['id']}"
    assert client.patch(url, json={"days": ["mon"]}).status_code == 401
    assert client.post("/api/routines", json={"mission_id": "x", "wake": "09:00"}).status_code == 401
    assert client.get(f"{url}/trial").status_code == 401


# ---------- the routine ----------


def test_days_wake_and_goal(client):
    routine = edit(client, "PATCH", days=["fri", "mon"], wake="06:20", remind_every=10).json()
    assert routine["days"] == ["mon", "fri"] and routine["wake"] == "06:20"
    # Starting at a time, the goal comes when the parts end (05/11): its own time does not count
    goal = {"at": "07:50", "say": "¡Al autobús!"}
    assert edit(client, "PATCH", goal=goal).json()["goal"] == {
        "at": "07:25", "say": "¡Al autobús!", "image": None, "check_minutes": 0, "check_say": None}
    assert edit(client, "PATCH", goal=None).json()["ends"] == "07:25"


@pytest.mark.parametrize("body", [{"wake": "06:40"}, {"days": []}])
def test_times_that_do_not_add_up_are_refused(client, body):
    assert edit(client, "PATCH", **body).status_code == 422
    assert edit(client, "GET").json()["wake"] == "06:30"


def test_who_follows_it(client):
    bea, alex = create_child(client), create_child(client, name="Alex", preset="dinosaur")
    routine = edit(client, "PUT", "/kids", kids=[bea["id"]]).json()
    assert routine["every_child"] is False and routine["kids"] == [bea["id"]]
    assert edit(client, "PUT", "/kids", kids=[alex["id"], bea["id"]]).json()["every_child"] is True
    assert edit(client, "PUT", "/kids", kids=[]).status_code == 422


def test_a_deleted_child_leaves_the_routines(client, data_dir):
    bea, alex = create_child(client), create_child(client, name="Alex", preset="dinosaur")
    edit(client, "PUT", "/kids", kids=[bea["id"]])
    client.delete(f"/api/children/{bea['id']}", headers=PARENT)
    routine = saved(data_dir)["routines"][0]
    assert routine["kids"] == []  # nobody listed: every child


def test_delete_a_routine_keeps_the_mission(client, morning):
    assert edit(client, "DELETE").status_code == 204
    assert client.get("/api/routines").json() == []
    assert client.get(f"/api/missions/{morning['mission_id']}").json()["routine"] is None


# ---------- its parts: the tasks ----------


def test_what_is_its_own_of_each_part(client):
    first = edit(client, "GET").json()["parts"][0]["id"]
    changes = {"minutes": 3, "say": "A lavarse.", "warnings": [2], "spoken": "el aseo"}
    part = edit(client, "PATCH", f"/parts/{first}", **changes).json()["parts"][0]
    assert part["minutes"] == 3 and part["say"] == "A lavarse." and part["warnings"] == [2]
    assert part["name"] == "el aseo" and part["text"] == PARTS[0][0]
    part = edit(client, "PATCH", f"/parts/{first}", spoken="  ").json()["parts"][0]
    assert part["name"] == PARTS[0][0][:1].lower() + PARTS[0][0][1:]  # empty: as the task says it
    assert edit(client, "PATCH", "/parts/nope", minutes=3).status_code == 404
    assert edit(client, "PATCH", f"/parts/{first}", minutes=0).status_code == 422


@pytest.mark.parametrize("method, path", [
    ("POST", "/parts"), ("POST", "/parts/import"), ("POST", "/parts/delete"), ("PUT", "/parts/order"),
    ("DELETE", "/parts/x"), ("PUT", "/photo"), ("PUT", "/parts/x/photo"),
])
def test_tasks_are_changed_in_the_mission_not_here(client, method, path):
    assert edit(client, method, path, x=1).status_code in (404, 405)


def test_only_the_steps_some_child_of_the_routine_has_on(client, morning):
    bea, noa = create_child(client), create_child(client, name="Noa", preset="fox")
    edit(client, "PUT", "/kids", kids=[bea["id"]])
    mission = client.get(f"/api/missions/{morning['mission_id']}").json()
    step = mission["tasks"][2]["steps"][0]
    url = f"/api/missions/{mission['id']}/children/{{}}/items/{step['id']}"
    client.put(url.format(noa["id"]), json={"active": False}, headers=PARENT)  # not in the routine: no matter
    assert [s["text"] for s in edit(client, "GET").json()["parts"][2]["steps"]] == ["Dientes", "Cara"]
    client.put(url.format(bea["id"]), json={"active": False}, headers=PARENT)
    assert [s["text"] for s in edit(client, "GET").json()["parts"][2]["steps"]] == ["Cara"]


def test_trial_keeps_the_routines_own_times(client, clock):
    trial = edit(client, "GET", "/trial").json()
    assert trial["trial"] is True and trial["wake"] == "06:30"
    assert [(p["start"], p["end"]) for p in trial["parts"]][:2] == [("06:35", "06:45"), ("06:45", "07:00")]
    assert trial["goal"]["at"] == "07:30"
    assert trial["now"] == pytest.approx(6 * 60 + 30)  # as if it were 6:30, whatever the time now
    assert descriptions(client, limit=1) == ["Probaste la rutina «Despegue»"]
    assert client.get("/api/routines/current").json() is None  # nothing really rings


def test_trial_from_a_part(client):
    trial = edit(client, "GET", "/trial?from=2").json()
    assert trial["parts"][2]["start"] == "07:00"
    assert trial["now"] == pytest.approx(7 * 60 - 20 / 60)  # 20 seconds before: its countdown is heard
    assert edit(client, "GET", "/trial?from=9").status_code == 404


# ---------- moved on some days ----------


def test_a_day_with_everything_later(client, clock):
    routine = edit(client, "PATCH", offsets={"tue": 15, "wed": 0}).json()
    assert routine["offsets"] == {"tue": 15}  # 0 means not moved
    clock.moment = datetime(2026, 11, 3, 6, 40, tzinfo=MADRID)  # Tuesday 6:40: not yet (it rings at 6:45)
    assert client.get("/api/routines/current").json() is None
    clock.moment = datetime(2026, 11, 3, 6, 50, tzinfo=MADRID)
    on = client.get("/api/routines/current").json()
    assert on["wake"] == "06:45" and on["parts"][0]["start"] == "06:50" and on["goal"]["at"] == "07:45"
    clock.moment = datetime(2026, 11, 2, 6, 40, tzinfo=MADRID)  # Monday: as usual
    assert client.get("/api/routines/current").json()["wake"] == "06:30"


def test_moved_days_count_for_overlaps_and_must_stay_in_their_day(client):
    other = create(client, another_mission(client), wake="08:00")
    assert other.status_code == 201
    assert edit(client, "PATCH", offsets={"tue": 45}).status_code == 409  # Mañana would end at 8:15 on Tuesday
    assert edit(client, "PATCH", offsets={"tue": -500}).status_code == 422


# ---------- notices before it rings ----------


def test_notices_before_it_rings(client, clock):
    notices = [{"minutes": 20, "say": "Es hora de despertar a los niños."}, {"minutes": 5, "say": "Cinco minutos."}]
    routine = edit(client, "PATCH", notices=notices).json()
    assert routine["notices"] == notices
    clock.moment = datetime(2026, 11, 2, 5, 0, tzinfo=MADRID)
    assert client.get("/api/routines/notices").json()["notices"] == [
        {"routine": client.get("/api/routines").json()[0]["id"], "at": 6 * 60 + 10, "say": "Es hora de despertar a los niños."},
        {"routine": client.get("/api/routines").json()[0]["id"], "at": 6 * 60 + 25, "say": "Cinco minutos."},
    ]
    edit(client, "PATCH", offsets={"tue": 15})
    clock.moment = datetime(2026, 11, 3, 5, 0, tzinfo=MADRID)  # Tuesday: they move with it
    assert client.get("/api/routines/notices").json()["notices"][0]["at"] == 6 * 60 + 25
    assert edit(client, "PATCH", notices=[{"minutes": 0, "say": "x"}]).status_code == 422


# ---------- "Empieza a las" or "Termina a las", and the alarm ----------


def test_a_new_routine_that_ends_at_a_time(client):
    mission = another_mission(client, "Noche", ("Pijama",))
    routine = create(client, mission, ends="20:30").json()
    assert routine["anchor"] == "end" and routine["goal"] == {"image": None, "at": "20:30", "say": "¡Rutina terminada!",
                                                              "check_minutes": 0, "check_say": None}
    assert parts(routine) == [("Pijama", "20:25", "20:30")]
    assert routine["wake"] == "20:25" and routine["alarm_before"] == 0
    # Another task: the end stays, the start moves back
    add_task(client, mission["id"], "Dientes")
    routine = client.get(f"/api/routines/{routine['id']}").json()
    assert parts(routine) == [("Pijama", "20:20", "20:25"), ("Dientes", "20:25", "20:30")]
    assert routine["starts"] == "20:20" and routine["ends"] == "20:30"


def test_a_new_routine_needs_one_time(client):
    mission = another_mission(client)
    for times in ({}, {"starts": "20:00", "ends": "21:00"}):
        assert create(client, mission, **times).status_code == 422


def test_ending_at_its_goal_keeps_that_time(client):
    routine = edit(client, "PATCH", anchor="end").json()
    # The goal stays at 7:30: the parts move up to it, one after the other, up to its
    # 5 minutes of checking the missions, and it still rings 5 minutes before
    assert routine["goal"]["at"] == "07:30" and routine["parts"][-1]["end"] == "07:25"
    assert routine["starts"] == "06:35" and routine["wake"] == "06:30" and routine["alarm_before"] == 5
    first = routine["parts"][0]["id"]
    routine = edit(client, "PATCH", f"/parts/{first}", minutes=15).json()  # 5 more minutes
    assert routine["starts"] == "06:30" and routine["wake"] == "06:25" and routine["ends"] == "07:30"
    # "Termina a las 8:00": the parts end then, and the 5 minutes of checking come after
    routine = edit(client, "PATCH", ends="08:00").json()
    assert routine["parts"][-1]["end"] == "08:00" and routine["goal"]["at"] == "08:05"
    assert routine["starts"] == "07:05"
    # The goal is a must
    assert edit(client, "PATCH", goal=None).status_code == 422


def test_ending_at_a_time_without_a_goal_gets_one(client):
    edit(client, "PATCH", goal=None)
    routine = edit(client, "PATCH", anchor="end").json()
    assert routine["goal"] == {"image": None, "at": "07:25", "say": "¡Rutina terminada!",
                               "check_minutes": 0, "check_say": None}


def test_starts_at_and_the_alarm(client):
    routine = edit(client, "PATCH", starts="06:30").json()
    assert routine["starts"] == "06:30" and routine["wake"] == "06:25"  # still 5 minutes before
    routine = edit(client, "PATCH", alarm_before=0).json()
    assert routine["wake"] == "06:30" and routine["alarm"] is True
    routine = edit(client, "PATCH", alarm_before=10).json()
    assert routine["wake"] == "06:20"
    routine = edit(client, "PATCH", alarm=False).json()
    assert routine["alarm"] is False and routine["wake"] == "06:30"  # no ring: it opens at its first part


def test_a_new_start_moves_the_whole_routine(client):
    # The parts one after the other from there, and the goal when they end
    routine = edit(client, "PATCH", starts="06:40").json()
    assert routine["starts"] == "06:40" and routine["wake"] == "06:35"
    assert parts(routine)[:2] == [("Preparar el desayuno", "06:40", "06:50"), ("Desayuno", "06:50", "07:05")]
    assert routine["goal"]["at"] == "07:35"


def test_the_screen_knows_if_it_rings(client, clock):
    edit(client, "PATCH", alarm=False)
    clock.moment = datetime(2026, 11, 2, 6, 40, tzinfo=MADRID)
    assert client.get("/api/routines/current").json()["alarm"] is False


def test_by_hand_it_neither_starts_nor_ends_at_a_time(client):
    edit(client, "PATCH", anchor="end")
    routine = edit(client, "PATCH", wake=None).json()
    assert routine["manual"] is True and routine["anchor"] == "start"
    assert edit(client, "PATCH", anchor="end").status_code == 422


# ---------- "Lo que dice la voz" (rutinas-5) ----------


def test_the_routines_own_sentences(client, clock):
    routine = edit(client, "PATCH", greeting="¡Arriba!", last_countdown="  ", early_goal="¡Bien!").json()
    assert routine["greeting"] == "¡Arriba!" and routine["early_goal"] == "¡Bien!"
    assert routine["last_countdown"] is None  # empty: the usual one
    clock.moment = datetime(2026, 11, 2, 6, 40, tzinfo=MADRID)
    on = client.get("/api/routines/current").json()
    assert on["greeting"] == "¡Arriba!" and on["early_goal"] == "¡Bien!" and "name" not in on["goal"]
    assert edit(client, "PATCH", greeting=None).json()["greeting"] is None


# ---------- checking the missions, part of the goal (rutinas-6) ----------


def test_the_goals_checking_moves_the_parts(client):
    routine = edit(client, "PATCH", anchor="end").json()
    goal = routine["goal"]
    routine = edit(client, "PATCH", goal={**goal, "check_minutes": 10}).json()
    assert routine["goal"]["at"] == "07:30" and routine["parts"][-1]["end"] == "07:20"
    routine = edit(client, "PATCH", goal={**routine["goal"], "check_minutes": 0}).json()
    assert routine["parts"][-1]["end"] == "07:30"


def test_warnings_about_the_next_part(client, clock):
    assert edit(client, "GET").json()["warn_about"] == "end"
    assert edit(client, "PATCH", warn_about="next").json()["warn_about"] == "next"
    assert edit(client, "PATCH", warn_about="later").status_code == 422
    clock.moment = datetime(2026, 11, 2, 6, 40, tzinfo=MADRID)
    assert client.get("/api/routines/current").json()["warn_about"] == "next"
