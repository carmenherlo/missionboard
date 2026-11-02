from datetime import datetime, timedelta, timezone

import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage.config_migrations import upgrade
from app.storage.config_store import config_path
from tests.conftest import PARENT
from tests.test_missions import add_step, create_child, create_mission, patch, saved, upload
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


URL = "/api/routines/manana"


def edit(client, method, path="", **body):
    return client.request(method, f"{URL}{path}", json=body or None, headers=PARENT)


def parts(routine):
    return [(p["name"], p["start"], p["end"]) for p in routine["parts"]]


# ---------- the list and a new routine ----------


def test_the_list_has_the_morning_routine(client):
    routines = client.get("/api/routines").json()
    assert [r["name"] for r in routines] == ["Mañana"]
    morning = routines[0]
    assert morning["every_child"] is True and morning["ends"] == "07:45"
    assert morning["parts"][0]["id"] == "manana-1" and morning["parts"][0]["image_url"].endswith("cooking.svg")
    assert morning["conflicts"] == []


def test_a_new_routine_rings_at_its_time_with_one_part(client):
    response = client.post("/api/routines", json={"name": "Deberes", "wake": "17:00"}, headers=PARENT)
    assert response.status_code == 201
    routine = response.json()
    assert routine["days"] == ["mon", "tue", "wed", "thu", "fri"]
    assert parts(routine) == [("la primera parte", "17:05", "17:10")]
    assert descriptions(client, limit=1) == ["Creaste la rutina «Deberes»"]


def test_two_routines_cannot_ring_at_the_same_time(client):
    assert client.post("/api/routines", json={"name": "X", "wake": "07:00"}, headers=PARENT).status_code == 409
    other = client.post("/api/routines", json={"name": "Finde", "wake": "07:00"}, headers=PARENT)
    assert other.status_code == 409  # same days by default
    weekend = client.post("/api/routines", json={"name": "Finde", "wake": "09:00"}, headers=PARENT).json()
    client.patch(f"/api/routines/{weekend['id']}", json={"days": ["sat", "sun"]}, headers=PARENT)
    # On the weekend, the same hours as the morning one are fine
    client.patch(f"/api/routines/{weekend['id']}/parts/{weekend['parts'][0]['id']}", json={"at": "07:05"},
                 headers=PARENT)
    assert client.patch(f"/api/routines/{weekend['id']}", json={"wake": "07:00"}, headers=PARENT).status_code == 200


def test_changes_need_the_parent_code(client):
    assert client.patch(URL, json={"name": "X"}).status_code == 401
    assert client.post("/api/routines", json={"name": "X", "wake": "09:00"}).status_code == 401
    assert client.get(f"{URL}/trial").status_code == 401


# ---------- the routine ----------


def test_name_days_wake_and_goal(client, data_dir):
    routine = edit(client, "PATCH", name="Cole", days=["fri", "mon"], wake="06:20", remind_every=10).json()
    assert routine["name"] == "Cole" and routine["days"] == ["mon", "fri"] and routine["wake"] == "06:20"
    goal = {"name": "el autobús", "at": "07:50", "say": "¡Al autobús!"}
    assert edit(client, "PATCH", goal=goal).json()["goal"] == {**goal, "image": None}
    assert edit(client, "PATCH", goal=None).json()["ends"] == "07:35"
    assert saved(data_dir)["routines"][0]["name"] == "Cole"


@pytest.mark.parametrize("body", [{"wake": "06:40"}, {"goal": {"name": "x", "at": "07:30"}}, {"days": []}])
def test_times_that_do_not_add_up_are_refused(client, body):
    assert edit(client, "PATCH", **body).status_code == 422
    assert client.get(URL).json()["wake"] == "06:30"


def test_who_it_is_for_and_their_mission(client):
    bea, alex = create_child(client), create_child(client, name="Alex", preset="dinosaur")
    despegue = create_mission(client, bea["id"], name="Despegue").json()
    routine = edit(client, "PUT", "/kids", kids=[bea["id"]]).json()
    assert routine["every_child"] is False and routine["kids"] == [bea["id"]]
    assert edit(client, "PUT", "/kids", kids=[alex["id"], bea["id"]]).json()["every_child"] is True
    assert edit(client, "PUT", "/kids", kids=[]).status_code == 422
    assert edit(client, "PUT", f"/missions/{bea['id']}", mission_id=despegue["id"]).json()["missions"] == {
        bea["id"]: despegue["id"]}
    assert edit(client, "PUT", f"/missions/{alex['id']}", mission_id=despegue["id"]).status_code == 422
    assert edit(client, "PUT", f"/missions/{bea['id']}", mission_id=None).json()["missions"] == {bea["id"]: None}


def test_a_mission_closing_before_the_routine_ends_is_warned(client):
    bea = create_child(client)
    despegue = create_mission(client, bea["id"], name="Despegue").json()
    patch(client, despegue["id"], schedule={"start": "06:00", "end": "07:00"})
    routine = edit(client, "PUT", f"/missions/{bea['id']}", mission_id=despegue["id"]).json()
    assert routine["conflicts"] == [{"child": "Bea", "mission": "Despegue", "mission_id": despegue["id"],
                                     "closes": "07:00", "ends": "07:45"}]


def test_a_deleted_child_leaves_the_routines(client, data_dir):
    bea, alex = create_child(client), create_child(client, name="Alex", preset="dinosaur")
    edit(client, "PUT", "/kids", kids=[bea["id"]])
    client.delete(f"/api/children/{bea['id']}", headers=PARENT)
    routine = saved(data_dir)["routines"][0]
    assert routine["kids"] == [] and bea["id"] not in routine["missions"]  # nobody listed: every child


def test_delete_a_routine(client):
    assert client.delete(URL, headers=PARENT).status_code == 204
    assert client.get("/api/routines").json() == []


# ---------- its parts ----------


def test_add_change_and_remove_parts(client):
    routine = edit(client, "POST", "/parts", name="lavarse las manos").json()
    new = routine["parts"][-1]
    assert (new["name"], new["start"], new["end"]) == ("lavarse las manos", "07:35", "07:40")
    assert new["image_suggested"] is True or new["image"] is None
    changes = {"minutes": 3, "say": "A lavarse.", "tasks": [" Jabón ", ""], "warnings": [2], "check_mission": True,
               "image": "fluent/soap"}
    part = edit(client, "PATCH", f"/parts/{new['id']}", **changes).json()["parts"][-1]
    assert part["minutes"] == 3 and part["tasks"] == ["Jabón"] and part["warnings"] == [2]
    assert part["image"] == "fluent/soap" and part["image_suggested"] is False
    assert edit(client, "DELETE", f"/parts/{new['id']}").status_code == 200
    assert descriptions(client, limit=1) == ["Quitaste «lavarse las manos» de la rutina «Mañana»"]


def test_a_part_at_its_own_time_or_right_after(client):
    routine = edit(client, "PATCH", "/parts/manana-3", at="07:02").json()
    assert parts(routine)[2] == ("el aseo", "07:02", "07:07")
    assert edit(client, "PATCH", "/parts/manana-3", at="06:50").status_code == 422  # during breakfast
    routine = edit(client, "PATCH", "/parts/manana-3", at=None).json()
    assert parts(routine)[2] == ("el aseo", "07:00", "07:05")


def test_reorder_and_the_start_time_goes_with_the_first_part(client):
    order = ["manana-1", "manana-2", "manana-4", "manana-3", "manana-5", "manana-6", "manana-7"]
    routine = edit(client, "PUT", "/parts/order", ids=order).json()
    assert parts(routine)[2:4] == [("vestirse", "07:00", "07:07"), ("el aseo", "07:07", "07:12")]
    order = ["manana-2", "manana-1", "manana-4", "manana-3", "manana-5", "manana-6", "manana-7"]
    assert edit(client, "PUT", "/parts/order", ids=order).status_code == 422  # breakfast keeps its 6:45
    edit(client, "PATCH", "/parts/manana-2", at=None)
    routine = edit(client, "PUT", "/parts/order", ids=order).json()
    assert parts(routine)[:2] == [("el desayuno", "06:35", "06:50"), ("la preparación del desayuno", "06:50", "07:00")]


def test_removing_the_first_part_keeps_the_times(client):
    routine = edit(client, "DELETE", "/parts/manana-1").json()
    assert parts(routine)[0] == ("el desayuno", "06:45", "07:00")


def test_the_last_part_cannot_be_removed(client):
    routine = client.post("/api/routines", json={"name": "Una", "wake": "12:00"}, headers=PARENT).json()
    url = f"/api/routines/{routine['id']}/parts/{routine['parts'][0]['id']}"
    assert client.delete(url, headers=PARENT).status_code == 422


def test_a_part_photo(client, data_dir):
    routine = upload(client, f"{URL}/parts/manana-3/photo").json()
    assert routine["parts"][2]["image"].startswith("photo/")
    assert client.get(routine["parts"][2]["image_url"]).status_code == 200


# ---------- "Probar ahora" ----------


def test_trial_keeps_the_routines_own_times(client, clock):
    trial = client.get(f"{URL}/trial", headers=PARENT).json()
    assert trial["trial"] is True and trial["wake"] == "06:30"
    assert [(p["start"], p["end"]) for p in trial["parts"]][:2] == [("06:35", "06:45"), ("06:45", "07:00")]
    assert trial["goal"]["at"] == "07:45"
    assert trial["now"] == pytest.approx(6 * 60 + 30)  # as if it were 6:30, whatever the time now
    assert descriptions(client, limit=1) == ["Probaste la rutina «Mañana»"]
    assert client.get("/api/routines/current").json() is None  # nothing really rings


def test_trial_from_a_part(client):
    trial = client.get(f"{URL}/trial?from=2", headers=PARENT).json()
    assert trial["parts"][2]["start"] == "07:00"
    assert trial["now"] == pytest.approx(7 * 60 - 20 / 60)  # 20 seconds before: its countdown is heard
    assert client.get(f"{URL}/trial?from=9", headers=PARENT).status_code == 404


# ---------- migration 7 → 8 ----------


def test_v7_routines_get_each_childs_mission_by_name():
    doc = {
        "version": 7,
        "children": [{"id": "b"}, {"id": "a"}],
        "missions": [{"id": "m1", "child_id": "b", "name": "Despegue"}, {"id": "m2", "child_id": "a", "name": "Otra"}],
        "routines": [{"id": "manana", "name": "Mañana", "kids": [], "mission": "Despegue", "wake": "06:30",
                      "parts": [{"name": "uno", "at": "06:35", "minutes": 5}]}],
    }
    routine = upgrade(doc)["routines"][0]
    assert routine["kids"] == [] and routine["missions"] == {"b": "m1", "a": None}
    assert "mission" not in routine and routine["parts"][0]["id"] == "manana-1"


# ---------- moved on some days ----------


def test_a_day_with_everything_later(client, clock):
    routine = edit(client, "PATCH", offsets={"tue": 15, "wed": 0}).json()
    assert routine["offsets"] == {"tue": 15}  # 0 means not moved
    clock.moment = datetime(2026, 11, 3, 6, 40, tzinfo=MADRID)  # Tuesday 6:40: not yet (it rings at 6:45)
    assert client.get("/api/routines/current").json() is None
    clock.moment = datetime(2026, 11, 3, 6, 50, tzinfo=MADRID)
    on = client.get("/api/routines/current").json()
    assert on["wake"] == "06:45" and on["parts"][0]["start"] == "06:50" and on["goal"]["at"] == "08:00"
    clock.moment = datetime(2026, 11, 2, 6, 40, tzinfo=MADRID)  # Monday: as usual
    assert client.get("/api/routines/current").json()["wake"] == "06:30"


def test_moved_days_count_for_overlaps_and_must_stay_in_their_day(client):
    other = client.post("/api/routines", json={"name": "Otra", "wake": "08:00"}, headers=PARENT)
    assert other.status_code == 201
    assert edit(client, "PATCH", offsets={"tue": 30}).status_code == 409  # Mañana would end at 8:15 on Tuesday
    assert edit(client, "PATCH", offsets={"tue": -500}).status_code == 422


# ---------- notices before it rings ----------


def test_notices_before_it_rings(client, clock):
    notices = [{"minutes": 20, "say": "Es hora de despertar a los niños."}, {"minutes": 5, "say": "Cinco minutos."}]
    routine = edit(client, "PATCH", notices=notices).json()
    assert routine["notices"] == notices
    clock.moment = datetime(2026, 11, 2, 5, 0, tzinfo=MADRID)
    assert client.get("/api/routines/notices").json()["notices"] == [
        {"routine": "manana", "at": 6 * 60 + 10, "say": "Es hora de despertar a los niños."},
        {"routine": "manana", "at": 6 * 60 + 25, "say": "Cinco minutos."},
    ]
    edit(client, "PATCH", offsets={"tue": 15})
    clock.moment = datetime(2026, 11, 3, 5, 0, tzinfo=MADRID)  # Tuesday: they move with it
    assert client.get("/api/routines/notices").json()["notices"][0]["at"] == 6 * 60 + 25
    assert edit(client, "PATCH", notices=[{"minutes": 0, "say": "x"}]).status_code == 422


# ---------- parts from a mission ----------


def test_import_the_steps_of_a_mission_or_template(client):
    new = client.post("/api/routines", json={"name": "Tarde", "wake": "17:00"}, headers=PARENT).json()
    url = f"/api/routines/{new['id']}/parts/import"
    routine = client.post(url, json={"mission_id": "aterrizaje"}, headers=PARENT).json()  # a sample template
    names = [p["name"] for p in routine["parts"]][1:]
    assert names == ["quitarse los zapatos", "lavarse las manos", "merendar", "hacer los deberes"]
    assert routine["parts"][1]["image"] == "fluent/running-shoe" and routine["parts"][1]["minutes"] == 5
    bea = create_child(client)
    mission = create_mission(client, bea["id"], name="Noche").json()
    add_step(client, mission["id"], "Pijama")
    assert client.post(url, json={"mission_id": mission["id"]}, headers=PARENT).json()["parts"][-1]["name"] == "pijama"
    assert client.post(url, json={"mission_id": "nope"}, headers=PARENT).status_code == 404
    # Past the goal of the morning routine: refused, nothing changes
    assert edit(client, "POST", "/parts/import", mission_id="aterrizaje").status_code == 422
