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
    assert morning["every_child"] is True and morning["ends"] == "07:30"
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
    # Starting at a time, the goal comes when the parts end (05/11): its own time does not count
    goal = {"at": "07:50", "say": "¡Al autobús!"}
    assert edit(client, "PATCH", goal=goal).json()["goal"] == {
        "at": "07:25", "say": "¡Al autobús!", "image": None, "check_minutes": 0, "check_say": None}
    assert edit(client, "PATCH", goal=None).json()["ends"] == "07:25"
    assert saved(data_dir)["routines"][0]["name"] == "Cole"


@pytest.mark.parametrize("body", [{"wake": "06:40"}, {"days": []}])
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
                                     "closes": "07:00", "ends": "07:30"}]


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
    assert (new["name"], new["start"], new["end"]) == ("lavarse las manos", "07:25", "07:30")
    assert new["image_suggested"] is True or new["image"] is None
    changes = {"minutes": 3, "say": "A lavarse.", "tasks": [" Jabón ", ""], "warnings": [2],
               "image": "fluent/soap"}
    part = edit(client, "PATCH", f"/parts/{new['id']}", **changes).json()["parts"][-1]
    assert part["minutes"] == 3 and part["tasks"] == ["Jabón"] and part["warnings"] == [2]
    assert part["image"] == "fluent/soap" and part["image_suggested"] is False
    assert edit(client, "DELETE", f"/parts/{new['id']}").status_code == 200
    assert descriptions(client, limit=1) == ["Quitaste «lavarse las manos» de la rutina «Mañana»"]


def test_only_the_first_part_has_a_time(client):
    # Only the pinned time stays put (05/11): the others have only their minutes
    assert edit(client, "PATCH", "/parts/manana-3", at="07:02").status_code == 422
    routine = edit(client, "PATCH", "/parts/manana-1", at="06:40").json()
    assert parts(routine)[:2] == [("la preparación del desayuno", "06:40", "06:50"), ("el desayuno", "06:50", "07:05")]
    assert routine["goal"]["at"] == "07:35"


def test_reorder_and_the_start_time_goes_with_the_first_part(client):
    order = ["manana-1", "manana-2", "manana-4", "manana-3", "manana-5", "manana-6"]
    routine = edit(client, "PUT", "/parts/order", ids=order).json()
    assert parts(routine)[2:4] == [("vestirse", "07:00", "07:07"), ("el aseo", "07:07", "07:12")]
    order = ["manana-2", "manana-1", "manana-4", "manana-3", "manana-5", "manana-6"]
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
    assert trial["goal"]["at"] == "07:30"
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
    assert on["wake"] == "06:45" and on["parts"][0]["start"] == "06:50" and on["goal"]["at"] == "07:45"
    clock.moment = datetime(2026, 11, 2, 6, 40, tzinfo=MADRID)  # Monday: as usual
    assert client.get("/api/routines/current").json()["wake"] == "06:30"


def test_moved_days_count_for_overlaps_and_must_stay_in_their_day(client):
    other = client.post("/api/routines", json={"name": "Otra", "wake": "08:00"}, headers=PARENT)
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
    # Into the morning routine: its goal comes later (4 parts of 5 minutes)
    assert edit(client, "POST", "/parts/import", mission_id="aterrizaje").json()["goal"]["at"] == "07:50"


def test_remove_several_parts_at_once(client):
    routine = edit(client, "POST", "/parts/delete", ids=["manana-1", "manana-3", "manana-4"]).json()
    assert [p["name"] for p in routine["parts"]][:2] == ["el desayuno", "peinarse y acicalarse"]
    assert routine["parts"][0]["start"] == "06:45"
    assert edit(client, "POST", "/parts/delete", ids=[]).status_code == 422
    everything = [p["id"] for p in routine["parts"]]
    assert edit(client, "POST", "/parts/delete", ids=everything).status_code == 422  # one must stay
    assert edit(client, "POST", "/parts/delete", ids=["nope"]).status_code == 404


# ---------- "Empieza a las" or "Termina a las", and the alarm ----------


def test_a_new_routine_that_ends_at_a_time(client):
    body = {"name": "Noche", "ends": "20:30"}
    routine = client.post("/api/routines", json=body, headers=PARENT).json()
    assert routine["anchor"] == "end" and routine["goal"] == {"image": None, "at": "20:30", "say": "¡Rutina terminada!",
                                                         "check_minutes": 0, "check_say": None}
    assert parts(routine) == [("la primera parte", "20:25", "20:30")]
    assert routine["wake"] == "20:25" and routine["alarm_before"] == 0
    # Another part: the end stays, the start moves back
    routine = client.post(f"/api/routines/{routine['id']}/parts", json={"name": "el pijama"}, headers=PARENT).json()
    assert parts(routine) == [("la primera parte", "20:20", "20:25"), ("el pijama", "20:25", "20:30")]
    assert routine["starts"] == "20:20" and routine["ends"] == "20:30"


def test_a_new_routine_needs_one_time(client):
    for body in ({"name": "X"}, {"name": "X", "starts": "20:00", "ends": "21:00"}):
        assert client.post("/api/routines", json=body, headers=PARENT).status_code == 422


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
    # One after the other: no part at its own time, and the goal is a must
    second = routine["parts"][1]["id"]
    assert edit(client, "PATCH", f"/parts/{second}", at="07:20").status_code == 422
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
    assert parts(routine)[:2] == [("la preparación del desayuno", "06:40", "06:50"), ("el desayuno", "06:50", "07:05")]
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


def test_v9_routines_keep_what_they_said():
    doc = {"version": 9, "routines": [
        {"id": "manana", "wake": "06:30", "parts": [], "goal": {"name": "vuestra clase", "at": "07:45", "say": "¡Al cole!"}},
        {"id": "deberes", "wake": None, "parts": []},
    ]}
    morning, by_hand = upgrade(doc)["routines"]
    assert morning["goal"] == {"at": "07:45", "say": "¡Al cole!"}
    assert morning["greeting"] == "¡Buenos días!" and morning["last_countdown"] == "Diez segundos para salir."
    assert morning["early_goal"] == "¡Ya podéis salir de casa! ¡Que tengáis un buen día!"
    assert "greeting" not in by_hand and by_hand["last_countdown"] == "Diez segundos."
    assert "early_goal" not in by_hand


def test_the_routines_own_sentences(client, clock):
    routine = edit(client, "PATCH", greeting="¡Arriba!", last_countdown="  ", early_goal="¡Bien!").json()
    assert routine["greeting"] == "¡Arriba!" and routine["early_goal"] == "¡Bien!"
    assert routine["last_countdown"] is None  # empty: the usual one
    clock.moment = datetime(2026, 11, 2, 6, 40, tzinfo=MADRID)
    on = client.get("/api/routines/current").json()
    assert on["greeting"] == "¡Arriba!" and on["early_goal"] == "¡Bien!" and "name" not in on["goal"]
    assert edit(client, "PATCH", greeting=None).json()["greeting"] is None


# ---------- checking the missions, part of the goal (rutinas-6) ----------


def test_v11_signing_becomes_the_goals_checking():
    doc = {"version": 11, "routines": [{
        "id": "m", "wake": "07:00", "anchor": "end", "goal": {"at": "07:20", "say": "¡Fuera!"},
        "parts": [{"id": "a", "minutes": 15, "at": "07:00"},
                  {"id": "f", "minutes": 5, "say": "A firmar.", "check_mission": True}],
        "music": [{"id": "s", "song": "x", "start": "f", "until": None}],
    }]}
    routine = upgrade(doc)["routines"][0]
    assert [p["id"] for p in routine["parts"]] == ["a"] and "check_mission" not in routine["parts"][0]
    assert routine["goal"] == {"at": "07:20", "say": "¡Fuera!", "check_minutes": 5, "check_say": "A firmar."}
    assert routine["music"][0]["start"] == "goal"


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
