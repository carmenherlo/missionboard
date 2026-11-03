from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage.config_migrations import upgrade
from tests.conftest import PARENT
from tests.test_routines_editor import MADRID, URL, edit
from tests.test_settings import FixedClock

MP3 = b"ID3" + b"\x00" * 64


@pytest.fixture
def clock():
    return FixedClock(datetime(2026, 11, 2, 16, 20, 30, tzinfo=MADRID))


@pytest.fixture
def client(data_dir, clock):
    with TestClient(create_app(data_dir, clock=clock)) as c:
        yield c


def upload(client, name="¡A correr!", data=MP3, seconds=190.4):
    return client.post("/api/songs", params={"name": name, "seconds": seconds}, content=data,
                       headers={**PARENT, "Content-Type": "audio/mpeg"})


def part_ids(client):
    return [p["id"] for p in edit(client, "GET").json()["parts"]]


# ---------- the library ----------


def test_a_song_uploaded_renamed_and_heard(client, data_dir):
    song = upload(client).json()
    assert song["name"] == "¡A correr!" and song["seconds"] == 190.4 and song["used_in"] == []
    assert (data_dir / "sounds" / song["file"]).read_bytes() == MP3
    assert client.get(song["url"]).content == MP3
    renamed = client.patch(f"/api/songs/{song['id']}", json={"name": "Correr"}, headers=PARENT).json()
    assert renamed["name"] == "Correr"
    assert [s["name"] for s in client.get("/api/songs").json()] == ["Correr"]


def test_only_songs_and_only_parents(client):
    assert upload(client, data=b"\x89PNG\r\n\x1a\n" + b"\x00" * 20).status_code == 415
    assert upload(client, seconds=0).status_code == 422
    assert upload(client, name="  ").status_code == 422
    assert client.post("/api/songs", params={"name": "x", "seconds": 3}, content=MP3).status_code == 401


def test_a_song_deleted_leaves_the_routines(client, data_dir):
    song = upload(client).json()
    edit(client, "POST", "/music", song=song["id"], start=part_ids(client)[0])
    assert client.get("/api/songs").json()[0]["used_in"] == ["Mañana"]
    assert client.delete(f"/api/songs/{song['id']}", headers=PARENT).status_code == 204
    assert edit(client, "GET").json()["music"] == []
    assert not (data_dir / "sounds" / song["file"]).exists()


# ---------- in a routine ----------


def test_a_song_from_a_card_to_a_card(client):
    song = upload(client).json()["id"]
    parts = part_ids(client)
    routine = edit(client, "POST", "/music", song=song, start=parts[3]).json()
    music = routine["music"][0]
    assert music == {"id": music["id"], "song": song, "start": parts[3], "until": None}
    routine = edit(client, "PATCH", f"/music/{music['id']}", until=parts[5]).json()
    assert routine["music"][0]["until"] == parts[5]
    assert edit(client, "PATCH", f"/music/{music['id']}", until=parts[1]).status_code == 422  # before it starts
    assert edit(client, "PATCH", f"/music/{music['id']}", until="goal").json()["music"][0]["until"] == "goal"
    assert edit(client, "PATCH", f"/music/{music['id']}", until=None).json()["music"][0]["until"] is None
    assert edit(client, "DELETE", f"/music/{music['id']}").json()["music"] == []


def test_two_songs_never_at_once(client):
    song = upload(client).json()["id"]
    parts = part_ids(client)
    music = edit(client, "POST", "/music", song=song, start=parts[1]).json()["music"][0]
    edit(client, "PATCH", f"/music/{music['id']}", until=parts[3])
    assert edit(client, "POST", "/music", song=song, start=parts[2]).status_code == 409
    assert edit(client, "POST", "/music", song=song, start=parts[1]).status_code == 409
    assert edit(client, "POST", "/music", song=song, start=parts[4]).status_code == 200
    assert edit(client, "POST", "/music", song=song, start="alarm").status_code == 200


def test_the_songs_follow_the_cards(client):
    song = upload(client).json()["id"]
    parts = part_ids(client)
    edit(client, "POST", "/music", song=song, start="alarm")
    music = edit(client, "POST", "/music", song=song, start=parts[2]).json()["music"]
    later = next(m for m in music if m["start"] == parts[2])
    edit(client, "PATCH", f"/music/{later['id']}", until=parts[4])
    # The part where it ended goes: it plays once
    routine = edit(client, "DELETE", f"/parts/{parts[4]}").json()
    assert next(m for m in routine["music"] if m["start"] == parts[2])["until"] is None
    # The part where it started goes: so does the song
    routine = edit(client, "DELETE", f"/parts/{parts[2]}").json()
    assert [m["start"] for m in routine["music"]] == ["alarm"]
    # No alarm: from the first part
    routine = edit(client, "PATCH", alarm=False).json()
    assert [m["start"] for m in routine["music"]] == [routine["parts"][0]["id"]]


def test_the_screen_gets_where_each_song_plays(client, clock):
    song = upload(client).json()
    parts = part_ids(client)
    music = edit(client, "POST", "/music", song=song["id"], start="alarm").json()["music"][0]
    edit(client, "PATCH", f"/music/{music['id']}", until=parts[1])
    clock.moment = datetime(2026, 11, 2, 6, 40, tzinfo=MADRID)
    on = client.get("/api/routines/current").json()
    assert on["music"] == [{"id": music["id"], "name": "¡A correr!", "url": song["url"], "seconds": 190.4,
                            "start": "alarm", "until": 1}]


def test_v10_routines_get_their_songs():
    doc = upgrade({"version": 10, "routines": [{"id": "manana", "parts": []}]})
    assert doc["songs"] == [] and doc["routines"][0]["music"] == []
