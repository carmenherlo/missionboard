from datetime import datetime, timedelta, timezone

import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import DEFAULT_SEASONS
from app.today.api import background_url
from app.storage.config_migrations import CURRENT_VERSION
from app.storage.config_store import config_path
from tests.conftest import PARENT
from tests.test_missions import add_step, add_task, create_child, create_mission, patch
from tests.test_settings import FixedClock

MADRID = timezone(timedelta(hours=1))
MONDAY = datetime(2026, 11, 2, 17, 10, tzinfo=MADRID)  # a Monday, in the afternoon


def write_config(data_dir, settings):
    data_dir.mkdir(parents=True)
    doc = {"version": CURRENT_VERSION, "settings": settings}
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
    """A mission with one task, with those steps ("steps" in what it returns: that task's)."""
    created = create_mission(client, name=name).json()
    if steps:
        task = add_task(client, created["id"], "Tarea").json()["tasks"][0]
        for text in steps:
            add_step(client, created["id"], task["id"], text)
    if fields:
        patch(client, created["id"], **fields)
    found = client.get(f"/api/missions/{created['id']}").json()
    return {**found, "steps": found["tasks"][0]["steps"] if steps else []}


def today(client, child):
    response = client.get(f"/api/children/{child['id']}/today")
    assert response.status_code == 200
    return response.json()


def states(client, child):
    return {m["name"]: m["state"] for m in today(client, child)["missions"]}


def mark(client, child, mission, item_id, checked=True):
    url = f"/api/children/{child['id']}/today/missions/{mission['id']}/marks/{item_id}"
    return client.put(url, json={"checked": checked})


def check(client, child, mission, step_index, checked=True):
    return mark(client, child, mission, mission["steps"][step_index]["id"], checked)


def steps_of(day_mission):
    return [s for task in day_mission["tasks"] for s in task["steps"]]


def note(client, child, kind, mission, step_index=None):
    body = {"kind": kind, "mission_id": mission["id"]}
    if step_index is not None:
        body["step_id"] = mission["steps"][step_index]["id"]
    return client.post(f"/api/children/{child['id']}/today/notes", json=body)


def descriptions(client, limit=20):
    return [e["description"] for e in client.get(f"/api/events?limit={limit}", headers=PARENT).json()["latest"]]


def set_active(client, mission, child, item_id, active):
    url = f"/api/missions/{mission['id']}/children/{child['id']}/items/{item_id}"
    return client.put(url, json={"active": active}, headers=PARENT)


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
    assert [s["text"] for s in steps_of(day["missions"][0])] == ["Uno", "Dos"]
    assert day["missions"][0]["colors"]["color"] == "#f6d700"  # its own colour: the first free one
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
    for step in steps_of(merienda):
        mark(client, bea, merienda, step["id"])
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
    assert [s["checked"] for s in steps_of(first["today"]["missions"][0])] == [True, False]

    last = check(client, bea, despegue, 1).json()
    assert last["completed"] is True and last["stars_earned"] == 1
    assert last["today"]["missions"][0]["state"] == "done"
    assert last["today"]["stars"] == 1
    assert descriptions(client, limit=4) == [
        "Bea desbloqueó el premio del día",  # it was the only mission of today
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
    assert [s["checked"] for s in steps_of(response.json()["today"]["missions"][0])] == [False, False]
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


def test_an_unknown_mark_or_a_task_with_steps(client, bea):
    uno = mission(client, bea, "Uno")
    assert mark(client, bea, uno, "nope").status_code == 404
    assert mark(client, bea, uno, uno["tasks"][0]["id"]).status_code == 404  # it has steps: they are checked


def test_a_new_day_starts_empty_and_keeps_the_stars(client, bea, clock):
    despegue = mission(client, bea, "Despegue", steps=("Paso", "Otro"))
    check(client, bea, despegue, 0)
    otra = mission(client, bea, "Otra", steps=("Paso",))
    check(client, bea, otra, 0)
    clock.moment = MONDAY + timedelta(days=1)
    day = today(client, bea)
    assert {m["name"]: m["state"] for m in day["missions"]} == {"Despegue": "open", "Otra": "open"}
    assert not any(s["checked"] for m in day["missions"] for s in steps_of(m))
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


# ---------- what each child has ----------


def test_every_mission_is_of_every_child_with_what_they_have_on(client, bea):
    alex = create_child(client, name="Alex", preset="dinosaur")
    despegue = mission(client, bea, "Despegue", steps=("Dientes", "Cara"))
    set_active(client, despegue, alex, despegue["steps"][1]["id"], False)
    assert [s["text"] for s in steps_of(today(client, bea)["missions"][0])] == ["Dientes", "Cara"]
    theirs = today(client, alex)["missions"][0]
    assert [s["text"] for s in steps_of(theirs)] == ["Dientes"] and theirs["total"] == 1
    # One step left for Alex: checking it completes theirs, not Bea's
    assert check(client, alex, despegue, 0).json()["completed"] is True
    assert check(client, alex, despegue, 1).status_code == 404
    assert today(client, bea)["missions"][0]["state"] == "open"


def test_a_task_without_steps_on_is_checked_itself(client, bea):
    despegue = mission(client, bea, "Despegue", steps=("Dientes",))
    task = despegue["tasks"][0]
    set_active(client, despegue, bea, despegue["steps"][0]["id"], False)
    card = today(client, bea)["missions"][0]["tasks"][0]
    assert card["marks_itself"] is True and card["steps"] == [] and card["checked"] is False
    assert mark(client, bea, despegue, task["id"]).json()["completed"] is True
    assert today(client, bea)["missions"][0]["tasks"][0]["checked"] is True


def test_a_task_with_everything_off_is_gone_and_with_nothing_the_mission_too(client, bea):
    despegue = mission(client, bea, "Despegue", steps=("Dientes",))
    set_active(client, despegue, bea, despegue["steps"][0]["id"], False)
    set_active(client, despegue, bea, despegue["tasks"][0]["id"], False)
    assert today(client, bea)["missions"] == []


def test_the_counter_counts_what_the_child_checks(client, bea):
    despegue = mission(client, bea, "Despegue", steps=("Dientes", "Cara"))
    alone = add_task(client, despegue["id"], "Despertarse").json()["tasks"][1]
    check(client, bea, despegue, 0)
    mark(client, bea, despegue, alone["id"])
    found = today(client, bea)["missions"][0]
    assert (found["done"], found["total"]) == (2, 3)
    assert [t["checked"] for t in found["tasks"]] == [False, True]
    assert check(client, bea, despegue, 1).json()["completed"] is True


# ---------- days of the tasks ----------


def patch_task(client, mission, task_id, **fields):
    return client.patch(f"/api/missions/{mission['id']}/tasks/{task_id}", json=fields, headers=PARENT)


def test_a_task_with_its_own_days(client, bea):
    alunizaje = mission(client, bea, "Alunizaje", steps=("Uno",))  # Monday
    other = add_task(client, alunizaje["id"], "Ropa").json()["tasks"][1]
    assert patch_task(client, alunizaje, other["id"], days=["tue"]).status_code == 200
    assert [t["text"] for t in today(client, bea)["missions"][0]["tasks"]] == ["Tarea"]
    assert patch_task(client, alunizaje, other["id"], days=None).json()["tasks"][1]["days"] is None
    assert len(today(client, bea)["missions"][0]["tasks"]) == 2


def test_only_days_of_the_mission_and_no_task_that_day_no_mission(client, bea):
    alunizaje = mission(client, bea, "Alunizaje", steps=("Uno",), days=["mon", "tue"])
    task = alunizaje["tasks"][0]
    assert patch_task(client, alunizaje, task["id"], days=["sun"]).status_code == 422
    patch_task(client, alunizaje, task["id"], days=["tue"])
    assert today(client, bea)["missions"] == []
    # All of the mission's days are the same as having none of its own
    assert patch_task(client, alunizaje, task["id"], days=["mon", "tue"]).json()["tasks"][0]["days"] is None


def test_a_task_loses_the_days_the_mission_loses(client, bea):
    alunizaje = mission(client, bea, "Alunizaje", steps=("Uno",), days=["mon", "tue"])
    patch_task(client, alunizaje, alunizaje["tasks"][0]["id"], days=["mon"])
    patch(client, alunizaje["id"], days=["tue"])
    assert today(client, bea)["missions"] == []


# ---------- opening a mission only today ----------


def test_a_parent_opens_a_mission_only_today_with_its_star(client, bea, clock):
    deberes = mission(client, bea, "Deberes", steps=("Uno",), schedule={"start": "15:00", "end": "17:00"})
    url = f"/api/children/{bea['id']}/today/missions/{deberes['id']}/open"
    assert client.post(url).status_code == 401
    assert client.post(url, headers=PARENT).json()["missions"][0]["state"] == "open"
    assert descriptions(client, limit=1) == ["Abriste «Deberes» solo por hoy para Bea"]
    alex = create_child(client, name="Alex", preset="dinosaur")
    assert states(client, alex) == {"Deberes": "closed"}  # only for that child
    assert check(client, bea, deberes, 0).json()["stars_earned"] == 1
    clock.moment = MONDAY + timedelta(days=1)
    assert states(client, bea) == {"Deberes": "closed"}


def test_an_upcoming_mission_can_be_opened_too(client, bea):
    alunizaje = mission(client, bea, "Alunizaje", schedule={"start": "19:30"})
    url = f"/api/children/{bea['id']}/today/missions/{alunizaje['id']}/open"
    assert client.post(url, headers=PARENT).json()["missions"][0]["state"] == "open"


# ---------- the season, the moment of the day and its picture ----------


@pytest.mark.parametrize("moment, season", [
    (datetime(2026, 1, 15, 12, 0, tzinfo=MADRID), "invierno"),  # the last of the list goes on
    (datetime(2026, 3, 19, 12, 0, tzinfo=MADRID), "invierno"),
    (datetime(2026, 3, 20, 12, 0, tzinfo=MADRID), "primavera"),
    (datetime(2026, 7, 1, 12, 0, tzinfo=MADRID), "verano"),
    (datetime(2026, 9, 23, 12, 0, tzinfo=MADRID), "otono"),
    (datetime(2026, 12, 21, 12, 0, tzinfo=MADRID), "invierno"),
])
def test_the_season(client, bea, clock, moment, season):
    clock.moment = moment
    assert f"/{season}/" in today(client, bea)["background_url"]


# Autumn: sunrise at 7:30, sunset at 19:00; 2 hours either way.
@pytest.mark.parametrize("time, moment", [
    ((5, 29), "noche"), ((5, 30), "manana"), ((9, 29), "manana"), ((9, 30), "dia"), ((16, 59), "dia"),
    ((17, 0), "tarde"), ((20, 59), "tarde"), ((21, 0), "noche"), ((23, 59), "noche"), ((0, 0), "noche"),
])
def test_the_moment_of_the_day(client, bea, clock, time, moment):
    clock.moment = MONDAY.replace(hour=time[0], minute=time[1])
    day = today(client, bea)
    assert day["moment"] == moment
    assert day["background_url"] == f"static/backgrounds/otono/{moment}.webp"
    assert client.get(day["background_url"]).status_code == 200


def test_every_season_has_its_four_pictures():
    for season in DEFAULT_SEASONS:
        for moment in ("manana", "dia", "tarde", "noche"):
            assert background_url(season.name, moment), (season.name, moment)


def test_the_seasons_can_be_changed_in_the_settings_and_with_no_picture_no_background(data_dir, clock):
    write_config(data_dir, {"seasons": [{"name": "siempre", "start": "01-01", "sunrise": "08:00", "sunset": "20:00"}]})
    with TestClient(create_app(data_dir, clock=clock)) as client:
        day = today(client, create_child(client))
        assert day["moment"] == "dia" and day["background_url"] is None


def test_seasons_out_of_order_stop_the_app(data_dir, clock):
    write_config(data_dir, {"seasons": [{"name": "b", "start": "06-01", "sunrise": "08:00", "sunset": "20:00"},
                                        {"name": "a", "start": "01-01", "sunrise": "08:00", "sunset": "20:00"}]})
    with pytest.raises(Exception):
        with TestClient(create_app(data_dir, clock=clock)):
            pass
