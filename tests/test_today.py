from datetime import datetime, timedelta, timezone

import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage.config_store import config_path
from tests.conftest import PARENT
from tests.test_missions import add_step, create_child, create_mission, patch
from tests.test_settings import FixedClock

MADRID = timezone(timedelta(hours=1))
MONDAY = datetime(2026, 11, 2, 17, 10, tzinfo=MADRID)  # a Monday, in the afternoon


def write_config(data_dir, settings):
    data_dir.mkdir(parents=True)
    doc = {"version": 5, "children": [], "missions": [], "templates": [], "settings": settings}
    config_path(data_dir).write_text(yaml.safe_dump(doc))


@pytest.fixture
def clock():
    return FixedClock(MONDAY)


@pytest.fixture
def client(data_dir, clock):
    with TestClient(create_app(data_dir, clock=clock)) as c:
        yield c


@pytest.fixture
def bea(client):
    return create_child(client, preset="unicorn")


def mission(client, child, name, steps=("Uno", "Dos"), **fields):
    created = create_mission(client, child["id"], name=name).json()
    for text in steps:
        add_step(client, created["id"], text)
    if fields:
        patch(client, created["id"], **fields)
    return client.get(f"/api/missions/{created['id']}").json()


def today(client, child):
    response = client.get(f"/api/children/{child['id']}/today")
    assert response.status_code == 200
    return response.json()


def states(client, child):
    return {m["name"]: m["state"] for m in today(client, child)["missions"]}


def check(client, child, mission, step_index, checked=True):
    step_id = mission["steps"][step_index]["id"]
    url = f"/api/children/{child['id']}/today/missions/{mission['id']}/steps/{step_id}"
    return client.put(url, json={"checked": checked})


def note(client, child, kind, mission, step_index=None):
    body = {"kind": kind, "mission_id": mission["id"]}
    if step_index is not None:
        body["step_id"] = mission["steps"][step_index]["id"]
    return client.post(f"/api/children/{child['id']}/today/notes", json=body)


def descriptions(client, limit=20):
    return [e["description"] for e in client.get(f"/api/events?limit={limit}", headers=PARENT).json()["latest"]]


# ---------- which missions, in which state ----------


def test_the_route_has_todays_missions_in_order(client, bea):
    mission(client, bea, "Despegue")
    mission(client, bea, "Fin de semana", days=["sat", "sun"])
    mission(client, bea, "A medio crear", steps=())
    mission(client, bea, "Aterrizaje")
    day = today(client, bea)
    assert [m["name"] for m in day["missions"]] == ["Despegue", "Aterrizaje"]
    assert day["day"] == "2026-11-02"
    assert day["child"]["name"] == "Bea"
    assert day["colors"] == {"color": "#9471e7", "strong": "#66558e", "soft": "#e9ddff", "on": "#ffffff"}
    assert day["stars"] == 0
    assert [s["text"] for s in day["missions"][0]["steps"]] == ["Uno", "Dos"]
    assert day["star_url"].endswith("/star.svg")


def test_states_by_schedule(client, bea, clock):
    mission(client, bea, "Deberes", schedule={"start": "15:00", "end": "17:00"})
    mission(client, bea, "Merienda", schedule={"start": "17:00"})
    mission(client, bea, "Alunizaje", schedule={"start": "19:30"})
    assert states(client, bea) == {"Deberes": "closed", "Merienda": "open", "Alunizaje": "upcoming"}
    clock.moment = MONDAY.replace(hour=16, minute=59)
    assert states(client, bea) == {"Deberes": "open", "Merienda": "upcoming", "Alunizaje": "upcoming"}


def test_the_focus_is_the_first_open_mission_or_else_the_next_one(client, bea, clock):
    mission(client, bea, "Deberes", schedule={"start": "15:00", "end": "17:00"})
    mission(client, bea, "Merienda")
    mission(client, bea, "Alunizaje", schedule={"start": "19:30"})
    day = today(client, bea)
    assert [m["name"] for m in day["missions"] if m["focus"]] == ["Merienda"]
    assert day["focus_is_now"] is True

    clock.moment = MONDAY.replace(hour=18)
    merienda = day["missions"][1]
    for index in range(2):
        check(client, bea, {**merienda, "id": merienda["id"]}, index)
    day = today(client, bea)
    assert [m["name"] for m in day["missions"] if m["focus"]] == ["Alunizaje"]
    assert day["focus_is_now"] is False


def test_the_weekday_is_the_one_of_the_app_day(data_dir, clock):
    write_config(data_dir, {"day_starts_at": "04:00"})
    clock.moment = datetime(2026, 11, 3, 1, 0, tzinfo=MADRID)  # Tuesday 01:00: still Monday for the app
    with TestClient(create_app(data_dir, clock=clock)) as client:
        bea = create_child(client)
        mission(client, bea, "Lunes", days=["mon"])
        assert [m["name"] for m in today(client, bea)["missions"]] == ["Lunes"]
        assert today(client, bea)["day"] == "2026-11-02"


def test_an_unknown_child(client):
    assert client.get("/api/children/nobody/today").status_code == 404


# ---------- checking steps ----------


def test_checking_every_step_completes_the_mission_and_gives_its_star(client, bea):
    despegue = mission(client, bea, "Despegue")
    first = check(client, bea, despegue, 0).json()
    assert first["completed"] is False and first["stars_earned"] == 0
    assert [s["checked"] for s in first["today"]["missions"][0]["steps"]] == [True, False]

    last = check(client, bea, despegue, 1).json()
    assert last["completed"] is True and last["stars_earned"] == 1
    assert last["today"]["missions"][0]["state"] == "done"
    assert last["today"]["stars"] == 1
    assert descriptions(client, limit=3)[:3] == [
        "Bea completó «Despegue» · +1 estrella",
        "Bea marcó «Dos» en «Despegue»",
        "Bea marcó «Uno» en «Despegue»",
    ]


def test_stars_per_mission_comes_from_the_settings(data_dir, clock):
    write_config(data_dir, {"stars_per_mission": 3})
    with TestClient(create_app(data_dir, clock=clock)) as client:
        bea = create_child(client)
        uno = mission(client, bea, "Uno", steps=("Paso",))
        assert check(client, bea, uno, 0).json()["stars_earned"] == 3
        assert today(client, bea)["stars"] == 3


def test_unchecking_before_finishing(client, bea):
    despegue = mission(client, bea, "Despegue")
    check(client, bea, despegue, 0)
    response = check(client, bea, despegue, 0, checked=False)
    assert response.status_code == 200
    assert [s["checked"] for s in response.json()["today"]["missions"][0]["steps"]] == [False, False]
    assert descriptions(client, limit=1) == ["Bea desmarcó «Uno» en «Despegue»"]


def test_a_done_mission_cannot_be_unchecked_and_its_star_is_won_once(client, bea):
    despegue = mission(client, bea, "Despegue", steps=("Paso",))
    check(client, bea, despegue, 0)
    assert check(client, bea, despegue, 0, checked=False).status_code == 409
    again = check(client, bea, despegue, 0).json()
    assert again["completed"] is False and again["stars_earned"] == 0
    assert today(client, bea)["stars"] == 1


def test_a_mission_that_is_not_open_cannot_be_checked(client, bea):
    alunizaje = mission(client, bea, "Alunizaje", schedule={"start": "19:30"})
    deberes = mission(client, bea, "Deberes", schedule={"start": "15:00", "end": "17:00"})
    assert check(client, bea, alunizaje, 0).status_code == 409
    assert check(client, bea, deberes, 0).status_code == 409


def test_another_childs_mission_or_an_unknown_step(client, bea):
    alex = create_child(client, name="Alex", preset="dinosaur")
    suya = mission(client, alex, "Suya")
    assert check(client, bea, suya, 0).status_code == 404
    url = f"/api/children/{alex['id']}/today/missions/{suya['id']}/steps/nope"
    assert client.put(url, json={"checked": True}).status_code == 404


def test_a_new_day_starts_empty_and_keeps_the_stars(client, bea, clock):
    despegue = mission(client, bea, "Despegue", steps=("Paso", "Otro"))
    check(client, bea, despegue, 0)
    otra = mission(client, bea, "Otra", steps=("Paso",))
    check(client, bea, otra, 0)
    clock.moment = MONDAY + timedelta(days=1)
    day = today(client, bea)
    assert {m["name"]: m["state"] for m in day["missions"]} == {"Despegue": "open", "Otra": "open"}
    assert not any(s["checked"] for m in day["missions"] for s in m["steps"])
    assert day["stars"] == 1


def test_steps_changed_during_the_day(client, bea):
    despegue = mission(client, bea, "Despegue", steps=("Uno", "Dos", "Tres"))
    check(client, bea, despegue, 0)
    check(client, bea, despegue, 1)
    # A parent removes the step left: the mission is complete with the next check of an existing one
    client.delete(f"/api/missions/{despegue['id']}/steps/{despegue['steps'][2]['id']}", headers=PARENT)
    assert today(client, bea)["missions"][0]["state"] == "open"
    check(client, bea, despegue, 1, checked=False)
    assert check(client, bea, despegue, 1).json()["completed"] is True


# ---------- notes for the log ----------


def test_notes_go_to_the_log(client, bea):
    merienda = mission(client, bea, "Merienda")
    alunizaje = mission(client, bea, "Alunizaje", schedule={"start": "19:30"})
    deberes = mission(client, bea, "Deberes", schedule={"start": "15:00", "end": "17:00"})
    assert note(client, bea, "mission_opened", merienda).status_code == 204
    note(client, bea, "step_spoken", merienda, 1)
    note(client, bea, "mission_locked", alunizaje)
    note(client, bea, "mission_locked", deberes)
    note(client, bea, "mission_locked", merienda)  # open: nothing to log
    assert descriptions(client, limit=4) == [
        "Bea tocó «Deberes», que se cerró a las 17:00",
        "Bea tocó «Alunizaje», que se abre a las 19:30",
        "Bea escuchó «Dos»",
        "Bea abrió «Merienda»",
    ]
    event = client.get("/api/events?limit=1", headers=PARENT).json()["latest"][0]
    assert event["zone"] == "child" and event["child_name"] == "Bea"


def test_a_bad_note_is_refused(client, bea):
    merienda = mission(client, bea, "Merienda")
    assert note(client, bea, "dancing", merienda).status_code == 422
    body = {"kind": "step_spoken", "mission_id": merienda["id"], "step_id": "nope"}
    assert client.post(f"/api/children/{bea['id']}/today/notes", json=body).status_code == 404


# ---------- moment of the day and its picture ----------


@pytest.mark.parametrize("time, moment", [
    ((5, 59), "noche"), ((6, 0), "amanecer"), ((12, 0), "dia"), ((17, 10), "tarde"),
    ((17, 30), "atardecer"), ((23, 0), "noche"),
])
def test_the_moment_of_the_day(client, bea, clock, time, moment):
    clock.moment = MONDAY.replace(hour=time[0], minute=time[1])
    assert today(client, bea)["moment"] == moment


def test_the_moments_can_be_changed_in_the_settings(data_dir, clock):
    write_config(data_dir, {"moments": [{"name": "dia", "start": "08:00"}, {"name": "noche", "start": "20:00"}]})
    with TestClient(create_app(data_dir, clock=clock)) as client:
        assert today(client, create_child(client))["moment"] == "dia"


def test_moments_out_of_order_stop_the_app(data_dir, clock):
    write_config(data_dir, {"moments": [{"name": "noche", "start": "20:00"}, {"name": "dia", "start": "08:00"}]})
    with pytest.raises(Exception):
        with TestClient(create_app(data_dir, clock=clock)):
            pass


def test_the_background_of_the_moment(client, bea, data_dir):
    assert today(client, bea)["background_url"] is None  # 17:10: tarde, no picture yet
    (data_dir / "backgrounds").mkdir()
    (data_dir / "backgrounds" / "tarde.png").write_bytes(b"\x89PNG fake")
    url = today(client, bea)["background_url"]
    assert url.startswith("/api/backgrounds/tarde?v=")
    assert client.get(url).content == b"\x89PNG fake"
    assert client.get("/api/backgrounds/noche").status_code == 404
    assert client.get("/api/backgrounds/..%2Fconfig").status_code == 404
