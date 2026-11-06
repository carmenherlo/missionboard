import pytest
import yaml

from app.children import avatars
from app.storage.config_store import config_path
from tests.conftest import PARENT

PURPLE = avatars.PRESETS_BY_ID["unicorn"]["color"]
GREEN = avatars.PRESETS_BY_ID["dinosaur"]["color"]


def create(client, **fields):
    body = {"name": "Bea", "preset": "unicorn", **fields}
    return client.post("/api/children", json=body, headers=PARENT)


def saved_children(data_dir):
    return yaml.safe_load(config_path(data_dir).read_text())["children"]


def test_avatars_catalog(client):
    body = client.get("/api/avatars").json()
    assert len(body["presets"]) == len(avatars.PRESETS)
    assert all(p["color"] in avatars.PALETTE_COLORS for p in body["presets"])
    for preset in body["presets"]:
        assert client.get(preset["image_url"]).status_code == 200, preset["id"]


def test_palette_and_animals(client):
    body = client.get("/api/avatars").json()
    ids = [entry["id"] for entry in body["palette"]]
    assert ids[:6] == ["yellow", "lilac", "green", "orange", "pink", "blue"]
    assert {p["color"] for p in body["presets"]} == {e["color"] for e in body["palette"]}  # every colour has an animal
    assert len({p["id"] for p in body["presets"]}) == len(body["presets"]) >= 20
    assert all({"color", "strong", "soft", "on", "label"} <= entry.keys() for entry in body["palette"])


def test_each_animal_has_its_natural_colour():
    colour = {e["id"]: e["color"] for e in avatars.PALETTE}
    natural = {"hamster": "peach", "crab": "pink", "owl": "brown", "butterfly": "red", "fox": "orange"}
    for animal, name in natural.items():
        assert avatars.PRESETS_BY_ID[animal]["color"] == colour[name], animal


def test_list_is_empty_without_config(client):
    assert client.get("/api/children").json() == []


def test_create_with_preset_takes_preset_color(client, data_dir):
    response = create(client, name="  Bea  ")
    assert response.status_code == 201
    child = response.json()
    assert child["name"] == "Bea"
    assert child["color"] == PURPLE
    assert set(child) == {"id", "name", "preset", "color"}
    assert saved_children(data_dir) == [child]
    assert client.get("/api/children").json() == [child]


@pytest.mark.parametrize(
    "method, path",
    [("post", "/api/children"), ("put", "/api/children/x"), ("delete", "/api/children/x")],
)
def test_writes_require_parent_code(client, method, path):
    response = client.request(method, path, json={}, headers={"X-Parent-Code": "nope"})
    assert response.status_code == 401
    assert client.request(method, path, json={}).status_code == 401


@pytest.mark.parametrize("name", ["", "   ", "x" * 31])
def test_invalid_name(client, name):
    assert create(client, name=name).status_code == 422


def test_unknown_preset(client):
    assert create(client, preset="dragon").status_code == 422


def test_presets_are_exclusive(client):
    assert create(client).status_code == 201
    assert create(client, name="Alex").status_code == 409
    assert create(client, name="Alex", preset="dinosaur").status_code == 201


def test_update_child(client):
    child = create(client).json()
    response = client.put(
        f"/api/children/{child['id']}",
        json={"name": "Beatriz", "preset": "dinosaur"},
        headers=PARENT,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Beatriz"
    assert response.json()["color"] == GREEN


def test_update_rejects_preset_of_other_child(client):
    create(client)
    alex = create(client, name="Alex", preset="dinosaur").json()
    response = client.put(
        f"/api/children/{alex['id']}",
        json={"name": "Alex", "preset": "unicorn"},
        headers=PARENT,
    )
    assert response.status_code == 409


def test_update_missing_child(client):
    response = client.put(
        "/api/children/missing",
        json={"name": "Bea", "preset": "unicorn"},
        headers=PARENT,
    )
    assert response.status_code == 404


def test_delete_child(client, data_dir):
    bea = create(client).json()
    alex = create(client, name="Alex", preset="dinosaur").json()
    assert client.delete(f"/api/children/{bea['id']}", headers=PARENT).status_code == 204
    assert [c["id"] for c in saved_children(data_dir)] == [alex["id"]]
    assert client.delete(f"/api/children/{bea['id']}", headers=PARENT).status_code == 404


def test_a_new_child_starts_with_the_stars_of_the_settings(client, data_dir):
    create(client)  # no setting: none
    assert client.get(f"/api/children/{client.get('/api/children').json()[0]['id']}/today").json()["stars"] == 0
    doc = yaml.safe_load(config_path(data_dir).read_text())
    doc["settings"]["starting_stars"] = 5
    config_path(data_dir).write_text(yaml.safe_dump(doc))
    alex = create(client, name="Alex", preset="dinosaur").json()
    assert client.get(f"/api/children/{alex['id']}/today").json()["stars"] == 5
