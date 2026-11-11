"""Ajustes and the switches on each screen (ajustes.html), through the API."""

from datetime import datetime, timedelta, timezone

import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage.config_store import config_path
from tests.conftest import PARENT
from tests.test_events import descriptions
from tests.test_routines import make_morning
from tests.test_settings import FixedClock

MADRID = timezone(timedelta(hours=1))
MONDAY = datetime(2026, 11, 2, 7, 2, 30, tzinfo=MADRID)


@pytest.fixture
def clock():
    return FixedClock(MONDAY)


@pytest.fixture
def client(data_dir, clock):
    with TestClient(create_app(data_dir, clock=clock)) as c:
        yield c


def patch(client, **body):
    return client.patch("/api/settings", json=body, headers=PARENT)


def test_only_parents_see_and_change_them(client):
    assert client.get("/api/settings").status_code == 401
    assert client.patch("/api/settings", json={"stars_per_mission": 2}).status_code == 401


def test_what_there_is_and_the_season_now(client):
    got = client.get("/api/settings", headers=PARENT).json()
    assert got["settings"]["stars_per_mission"] == 1 and got["features"]["shop"] is True
    assert [s["name"] for s in got["settings"]["seasons"]] == ["primavera", "verano", "otono", "invierno"]
    assert got["now"] == {"season": "otono", "moment": "manana",  # 7:02: the morning starts at 5:30
                          "background_url": "static/backgrounds/otono/manana.webp"}


def test_a_change_is_saved_in_config_yaml_and_logged(client, data_dir):
    got = patch(client, stars_per_mission=2, day_starts_at="04:00").json()
    assert got["settings"]["stars_per_mission"] == 2
    saved = yaml.safe_load(config_path(data_dir).read_text())["settings"]
    assert saved["stars_per_mission"] == 2 and saved["day_starts_at"] == "04:00"
    assert descriptions(client)[0] == "Cambiaste los ajustes · estrellas por misión: 2 · el día empieza a las 04:00"
    patch(client, stars_per_mission=2)  # nothing changes: nothing logged
    assert descriptions(client)[0].startswith("Cambiaste los ajustes · estrellas por misión: 2 ·")


@pytest.mark.parametrize("body", [
    {"stars_per_mission": -1},
    {"day_starts_at": "25:00"},
    {"routine_warn_minutes": 31},
])
def test_a_value_that_does_not_do_is_not_saved(client, body):
    assert patch(client, **body).status_code == 422
    assert client.get("/api/settings", headers=PARENT).json()["settings"]["stars_per_mission"] == 1


def seasons(client):
    return client.get("/api/settings", headers=PARENT).json()["settings"]["seasons"]


def test_seasons_changed_checked_and_back_to_the_apps(client):
    changed = seasons(client)
    changed[2] = {**changed[2], "start": "10-01", "dia": "10:00"}
    assert patch(client, seasons=changed).status_code == 200
    assert seasons(client)[2] == {"name": "otono", "start": "10-01", "manana": "05:30", "dia": "10:00",
                                  "tarde": "17:00", "noche": "21:00"}
    night_first = [*changed[:2], {**changed[2], "noche": "16:00"}, changed[3]]
    assert patch(client, seasons=night_first).status_code == 422
    out_of_order = [*changed[:2], {**changed[2], "start": "06-01"}, changed[3]]
    assert patch(client, seasons=out_of_order).status_code == 422
    got = client.post("/api/settings/seasons/reset", headers=PARENT).json()["settings"]
    assert got["seasons"][2]["start"] == "09-23" and got["seasons"][2]["dia"] == "09:30"


def test_switches_that_do_something(client):
    url = "/api/settings/features"
    got = client.patch(url, json={"shop": False, "daily_prize": False}, headers=PARENT).json()
    assert got["features"]["shop"] is False and got["features"]["daily_prize"] is False
    assert descriptions(client)[0] == "Cambiaste lo que está encendido · premio del día apagado · tienda apagada"
    assert client.patch(url, json={"shop": "no"}, headers=PARENT).status_code == 422


def test_routines_switched_off_do_not_ring_and_are_kept(client):
    routine = make_morning(client)
    assert client.get("/api/routines/current").json()["id"] == routine["id"]
    client.patch("/api/settings/features", json={"routines": False}, headers=PARENT)
    assert client.get("/api/routines/current").json() is None
    assert client.get("/api/routines/next").json() is None
    assert [r["id"] for r in client.get("/api/routines").json()] == [routine["id"]]
    client.patch("/api/settings/features", json={"routines": True}, headers=PARENT)
    assert client.get("/api/routines/current").json() is not None


def test_how_the_home_screen_looks_changed_in_ajustes_and_read_without_a_code(client, data_dir):
    got = client.get("/api/home").json()  # the home screen: no parent code
    assert got["look"] == {"background": True, "veil": 0, "name_pill": True, "ring_glow": "color", "ring_too": True,
                           "centre_light": "white", "strength": 2, "beat_seconds": 3.5, "shine": True}
    assert got["background_url"] == "static/backgrounds/otono/manana.webp"
    look = {**got["look"], "ring_glow": "vivid", "veil": 25, "beat_seconds": 5}
    assert patch(client, home=look).status_code == 200
    assert client.get("/api/home").json()["look"]["ring_glow"] == "vivid"
    assert yaml.safe_load(config_path(data_dir).read_text())["settings"]["home"]["veil"] == 25
    assert descriptions(client)[0] == "Cambiaste los ajustes · aspecto del inicio cambiado"
    for wrong in ({"veil": 30}, {"ring_glow": "gold"}, {"beat_seconds": 4}):
        assert patch(client, home={**look, **wrong}).status_code == 422
    client.post("/api/settings/home/reset", headers=PARENT)
    assert client.get("/api/home").json()["look"]["ring_glow"] == "color"
