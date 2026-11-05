import pytest
import yaml

from app.children import avatars
from app.storage.config_store import config_path
from tests.conftest import PARENT

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
PURPLE = avatars.PRESETS_BY_ID["unicorn"]["color"]
GREEN = avatars.PRESETS_BY_ID["dinosaur"]["color"]


def create(client, **fields):
    body = {"name": "Bea", "avatar_type": "preset", "preset": "unicorn", **fields}
    return client.post("/api/children", json=body, headers=PARENT)


def upload(client, child_id, data=JPEG, content_type="image/jpeg"):
    headers = {**PARENT, "Content-Type": content_type}
    return client.put(f"/api/children/{child_id}/photo", content=data, headers=headers)


def saved_children(data_dir):
    return yaml.safe_load(config_path(data_dir).read_text())["children"]


def test_avatars_catalog(client):
    body = client.get("/api/avatars").json()
    assert len(body["presets"]) == len(avatars.PRESETS)
    assert all(p["color"] in avatars.PALETTE_COLORS for p in body["presets"])
    for preset in body["presets"]:
        assert client.get(preset["image_url"]).status_code == 200, preset["id"]


def test_palette_and_picker(client):
    body = client.get("/api/avatars").json()
    ids = [entry["id"] for entry in body["palette"]]
    assert ids[:6] == ["yellow", "lilac", "green", "orange", "pink", "blue"]  # suggestion order
    assert sorted(i for column in body["picker_columns"] for i in column) == sorted(ids)
    assert {p["color"] for p in body["presets"]} == {e["color"] for e in body["palette"]}  # every colour has an animal
    assert len({p["id"] for p in body["presets"]}) == len(body["presets"]) >= 20
    assert all({"color", "strong", "soft", "on", "label"} <= entry.keys() for entry in body["palette"])


def test_list_is_empty_without_config(client):
    assert client.get("/api/children").json() == []


def test_create_with_preset_takes_preset_color(client, data_dir):
    response = create(client, name="  Bea  ", color=GREEN)
    assert response.status_code == 201
    child = response.json()
    assert child["name"] == "Bea"
    assert child["color"] == PURPLE
    assert child["photo_url"] is None
    assert saved_children(data_dir) == [{k: v for k, v in child.items() if k != "photo_url"}]
    assert client.get("/api/children").json() == [child]


@pytest.mark.parametrize(
    "method, path",
    [("post", "/api/children"), ("put", "/api/children/x"), ("delete", "/api/children/x")],
)
def test_writes_require_parent_code(client, method, path):
    response = client.request(method, path, json={}, headers={"X-Parent-Code": "nope"})
    assert response.status_code == 401
    assert client.request(method, path, json={}).status_code == 401


def test_photo_upload_requires_parent_code(client):
    child = create(client).json()
    response = client.put(
        f"/api/children/{child['id']}/photo", content=JPEG, headers={"Content-Type": "image/jpeg"}
    )
    assert response.status_code == 401


@pytest.mark.parametrize("name", ["", "   ", "x" * 31])
def test_invalid_name(client, name):
    assert create(client, name=name).status_code == 422


def test_unknown_preset(client):
    assert create(client, preset="dragon").status_code == 422


def test_photo_avatar_requires_palette_color(client):
    assert create(client, avatar_type="photo", preset=None, color="#000000").status_code == 422
    assert create(client, avatar_type="photo", preset=None).status_code == 422


def test_presets_are_exclusive(client):
    assert create(client).status_code == 201
    assert create(client, name="Alex").status_code == 409
    assert create(client, name="Alex", preset="dinosaur").status_code == 201


def test_photo_color_may_repeat(client):
    create(client)
    for name in ("Alex", "Leo"):
        response = create(client, name=name, avatar_type="photo", preset=None, color=PURPLE)
        assert response.status_code == 201


def test_photo_color_does_not_block_preset(client):
    create(client, name="Alex", avatar_type="photo", preset=None, color=PURPLE)
    assert create(client, name="Bea", preset="unicorn").status_code == 201


def test_update_child(client):
    child = create(client).json()
    response = client.put(
        f"/api/children/{child['id']}",
        json={"name": "Beatriz", "avatar_type": "preset", "preset": "dinosaur"},
        headers=PARENT,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Beatriz"
    assert response.json()["color"] == GREEN


def test_update_can_keep_own_color(client):
    child = create(client).json()
    response = client.put(
        f"/api/children/{child['id']}",
        json={"name": "Bea", "avatar_type": "photo", "color": PURPLE},
        headers=PARENT,
    )
    assert response.status_code == 200


def test_update_rejects_preset_of_other_child(client):
    create(client)
    alex = create(client, name="Alex", preset="dinosaur").json()
    response = client.put(
        f"/api/children/{alex['id']}",
        json={"name": "Alex", "avatar_type": "preset", "preset": "unicorn"},
        headers=PARENT,
    )
    assert response.status_code == 409


def test_update_missing_child(client):
    response = client.put(
        "/api/children/missing",
        json={"name": "Bea", "avatar_type": "preset", "preset": "unicorn"},
        headers=PARENT,
    )
    assert response.status_code == 404


def test_delete_child(client, data_dir):
    bea = create(client).json()
    alex = create(client, name="Alex", preset="dinosaur").json()
    assert client.delete(f"/api/children/{bea['id']}", headers=PARENT).status_code == 204
    assert [c["id"] for c in saved_children(data_dir)] == [alex["id"]]
    assert client.delete(f"/api/children/{bea['id']}", headers=PARENT).status_code == 404


def test_upload_and_get_photo(client, data_dir):
    child = create(client).json()
    response = upload(client, child["id"])
    assert response.status_code == 200
    updated = response.json()
    assert updated["avatar_type"] == "photo"
    assert updated["preset"] is None
    assert updated["color"] == PURPLE
    assert updated["photo_url"].startswith(f"api/children/{child['id']}/photo")

    photo = client.get(updated["photo_url"])
    assert photo.status_code == 200
    assert photo.content == JPEG
    assert photo.headers["content-type"] == "image/jpeg"
    assert (data_dir / "photos" / updated["photo"]).is_file()


def test_replacing_photo_removes_old_file(client, data_dir):
    child = create(client).json()
    first = upload(client, child["id"]).json()["photo"]
    second = upload(client, child["id"], PNG, "image/png").json()["photo"]
    assert first != second
    assert sorted(p.name for p in (data_dir / "photos").iterdir()) == [second]


def test_switching_to_preset_removes_photo(client, data_dir):
    child = create(client).json()
    upload(client, child["id"])
    response = client.put(
        f"/api/children/{child['id']}",
        json={"name": "Bea", "avatar_type": "preset", "preset": "unicorn"},
        headers=PARENT,
    )
    assert response.json()["photo"] is None
    assert list((data_dir / "photos").iterdir()) == []


def test_deleting_child_removes_photo(client, data_dir):
    child = create(client).json()
    upload(client, child["id"])
    client.delete(f"/api/children/{child['id']}", headers=PARENT)
    assert list((data_dir / "photos").iterdir()) == []


@pytest.mark.parametrize(
    "data, content_type, status",
    [
        (JPEG, "image/gif", 415),
        (PNG, "image/jpeg", 422),
        (b"not an image", "image/png", 422),
        (b"", "image/jpeg", 422),
    ],
)
def test_invalid_photo(client, data, content_type, status):
    child = create(client).json()
    assert upload(client, child["id"], data, content_type).status_code == status


def test_photo_too_large(client, monkeypatch):
    monkeypatch.setattr("app.images.photos.MAX_PHOTO_BYTES", 10)
    child = create(client).json()
    assert upload(client, child["id"]).status_code == 413


def test_child_without_photo_has_no_photo_endpoint(client):
    child = create(client).json()
    assert client.get(f"/api/children/{child['id']}/photo").status_code == 404
