import zipfile
from datetime import datetime, timedelta, timezone

import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage import db
from app.storage.config_migrations import CURRENT_VERSION
from app.storage.config_store import config_path
from tests.conftest import PARENT
from tests.test_settings import FixedClock

MADRID = timezone(timedelta(hours=1))
MONDAY = datetime(2026, 11, 2, 6, 45, tzinfo=MADRID)
OLD = {"version": 14, "parents": {"code": "9999"},
       "children": [{"id": "x", "name": "De antes", "preset": "fox", "color": "#e77300"}],
       "missions": [{"id": "m", "child_id": "x", "name": "Vieja", "steps": []}],
       "templates": [], "routines": [],
       "songs": [{"id": "s", "name": "Canción", "file": "s.mp3", "seconds": 10}]}


def write_old(data_dir):
    data_dir.mkdir(parents=True)
    config_path(data_dir).write_text(yaml.safe_dump(OLD))
    db.migrate(data_dir, db.MIGRATIONS[:6])
    for folder, name in (("photos", "a.jpg"), ("sounds", "s.mp3"), ("backgrounds", "dia.png")):
        (data_dir / folder).mkdir()
        (data_dir / folder / name).write_bytes(b"x")
    (data_dir / "config.yaml.v13.bak").write_text("old")
    (data_dir / "voices").mkdir()
    (data_dir / "voices" / "big.onnx").write_bytes(b"x")


@pytest.fixture
def clock():
    return FixedClock(MONDAY)


def start(data_dir, clock, samples=True):
    return TestClient(create_app(data_dir, clock=clock, samples=samples))


# ---------- from before family missions ----------


def test_an_old_file_is_kept_in_a_copy_and_everything_starts_again(data_dir, clock):
    write_old(data_dir)
    with start(data_dir, clock) as client:
        assert [c["name"] for c in client.get("/api/children").json()] == ["Bea", "Alex", "Noa"]
        assert [m["name"] for m in client.get("/api/missions").json()] == ["Despegue", "Aterrizaje", "Alunizaje"]
        assert client.post("/api/parents/unlock", json={"code": "9999"}).status_code == 401
        assert client.post("/api/parents/unlock", json={"code": "1234"}).status_code == 204
        # The library stays, and the examples' songs join it
        assert [s["name"] for s in client.get("/api/songs").json()] == ["Canción", "Buenos días, solecito", "Duerme, Estrellita"]
    doc = yaml.safe_load(config_path(data_dir).read_text())
    assert doc["version"] == CURRENT_VERSION and doc["parents"]["code"] == "1234"
    assert "templates" not in doc
    copy = next((data_dir / "backups").glob("antes-de-misiones-*.zip"))
    names = zipfile.ZipFile(copy).namelist()
    assert {"config.yaml", "missionboard.db", "photos/a.jpg", "sounds/s.mp3", "backgrounds/dia.png",
            "config.yaml.v13.bak"} <= set(names)
    assert not any(n.startswith("voices/") for n in names)
    assert yaml.safe_load(zipfile.ZipFile(copy).read("config.yaml"))["parents"]["code"] == "9999"
    assert not (data_dir / "photos").exists() and not (data_dir / "backgrounds").exists()
    assert (data_dir / "sounds" / "s.mp3").exists() and (data_dir / "voices" / "big.onnx").exists()
    assert not list(data_dir.glob("*.bak"))


def test_it_happens_once(data_dir, clock):
    write_old(data_dir)
    with start(data_dir, clock) as client:
        client.post("/api/children", json={"name": "Leo", "preset": "lion"}, headers=PARENT)
    with start(data_dir, clock) as client:
        assert "Leo" in [c["name"] for c in client.get("/api/children").json()]
    assert len(list((data_dir / "backups").glob("*.zip"))) == 1


def test_a_newer_file_stops_the_app_and_touches_nothing(data_dir, clock):
    data_dir.mkdir(parents=True)
    config_path(data_dir).write_text(yaml.safe_dump({"version": CURRENT_VERSION + 1}))
    with pytest.raises(Exception):
        with start(data_dir, clock):
            pass
    assert yaml.safe_load(config_path(data_dir).read_text()) == {"version": CURRENT_VERSION + 1}
    assert not (data_dir / "backups").exists()


# ---------- a new installation ----------


def test_tests_start_empty_and_nothing_is_written(data_dir, clock):
    with start(data_dir, clock, samples=False) as client:
        assert client.get("/api/children").json() == [] and client.get("/api/missions").json() == []
    assert not config_path(data_dir).exists()


@pytest.fixture
def examples(data_dir, clock):
    with start(data_dir, clock) as client:
        yield client


def test_the_examples(examples):
    client = examples
    children = client.get("/api/children").json()
    assert [(c["name"], c["preset"]) for c in children] == [("Bea", "fox"), ("Alex", "dinosaur"), ("Noa", "unicorn")]
    missions = {m["name"]: m for m in client.get("/api/missions").json()}
    assert missions["Despegue"]["color"] == "#2193d6" and missions["Aterrizaje"]["color"] == "#e77300"
    assert missions["Alunizaje"]["color"] == "#9471e7"
    assert missions["Despegue"]["days"] == ["mon", "tue", "wed", "thu", "fri"]
    assert missions["Alunizaje"]["days"] == ["mon", "tue", "wed", "thu", "fri", "sun"]
    assert [t["text"] for t in missions["Despegue"]["tasks"]] == [
        "Despertarse", "Desayunar", "Recoger el desayuno", "Aseo", "Vestirse", "Acicalarse", "Prepararse para salir"]
    assert missions["Aterrizaje"]["schedule"] == {"start": "12:00", "end": "18:00"}
    assert missions["Aterrizaje"]["routine"] is None
    every = [item for mission in missions.values() for task in mission["tasks"] for item in (task, *task["steps"])]
    assert all(item["image_url"] for item in every)  # every picture exists, the pajamas too
    for mission in missions.values():  # a task's picture is not one of its steps'
        for task in mission["tasks"]:
            assert task["image"] not in [step["image"] for step in task["steps"]]


def test_each_child_starts_with_five_stars_and_so_does_a_new_one(examples):
    client = examples
    first = client.get("/api/children").json()[0]
    assert client.get(f"/api/children/{first['id']}/today").json()["stars"] == 5
    leo = client.post("/api/children", json={"name": "Leo", "preset": "lion"}, headers=PARENT).json()
    assert client.get(f"/api/children/{leo['id']}/today").json()["stars"] == 5


def test_the_morning_of_the_examples(examples, clock):
    client = examples
    on = client.get("/api/routines/current").json()  # Monday 6:45
    assert on["name"] == "Despegue" and on["wake"] == "06:35" and on["alarm"] is True
    assert on["parts"][0]["start"] == "06:40" and on["parts"][-1]["end"] == "07:30" and on["goal"]["at"] == "07:35"
    assert [p["child"]["name"] for p in on["people"]] == ["Bea", "Alex"]
    assert [s["name"] for s in on["music"][0]["songs"]] == ["Buenos días, solecito"] and on["music"][0]["start"] == 0
    states = {
        c["name"]: client.get(f"/api/children/{c['id']}/today").json()["missions"][0]
        for c in client.get("/api/children").json()
    }
    assert states["Bea"]["state"] == "open" and states["Bea"]["schedule"] == {"start": "06:40", "end": "07:35"}
    assert states["Noa"]["state"] == "open" and states["Noa"]["schedule"] == {"start": "06:00", "end": "09:00"}


def test_the_examples_songs_are_in_the_library_and_play(examples, data_dir):
    client = examples
    songs = client.get("/api/songs").json()
    assert [s["name"] for s in songs] == ["Buenos días, solecito", "Duerme, Estrellita"]
    for song in songs:
        assert (data_dir / "sounds" / song["file"]).is_file()
        assert client.get(song["url"]).content[4:8] == b"ftyp"  # an m4a
    night = next(r for r in client.get("/api/routines").json() if r["name"] == "Alunizaje")
    assert night["music"][0]["start"] == "goal" and night["music"][0]["after_voice"] is True


def test_the_night_of_the_examples(examples, clock):
    client = examples
    clock.moment = MONDAY.replace(hour=19, minute=10)
    on = client.get("/api/routines/current").json()
    assert on["name"] == "Alunizaje" and on["alarm"] is False and on["goal"]["at"] == "19:30"
    assert len(on["parts"]) == 5 and on["parts"][0]["start"] == "18:55"
    assert len(on["people"]) == 3
    clock.moment = datetime(2026, 11, 6, 19, 10, tzinfo=MADRID)  # Friday: no clothes or bag to prepare
    on = client.get("/api/routines/current").json()
    assert [p["text"] for p in on["parts"]] == ["Recoger la cena", "Recoger la habitación", "Lavarse los dientes"]
    assert on["parts"][0]["start"] == "19:05"
    clock.moment = datetime(2026, 11, 7, 19, 10, tzinfo=MADRID)  # Saturday: not at all
    assert client.get("/api/routines/current").json() is None
    bea = client.get("/api/children").json()[0]
    assert client.get(f"/api/children/{bea['id']}/today").json()["missions"] == []
