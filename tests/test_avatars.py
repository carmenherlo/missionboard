import io
import zipfile

import yaml

from app.children import avatars
from app.storage.config_migrations import upgrade
from app.storage.config_store import config_path
from tests.conftest import PARENT

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 64
WEBP = b"RIFF\0\0\0\0WEBP" + b"\0" * 64
JPEG = b"\xff\xd8\xff" + b"\0" * 64
BROWN = "#a0663f"


def upload(client, data=PNG, name="Oso", color=BROWN, suggested=True, headers=PARENT):
    query = {"name": name, "color": color, "suggested": str(suggested).lower()}
    return client.post("/api/avatars", params=query, content=data, headers={**headers, "Content-Type": "image/png"})


def family(client):
    return client.get("/api/avatars").json()["family"]


def wear(client, avatar_id, name="Bea"):
    return client.post("/api/children", json={"name": name, "preset": avatar_id}, headers=PARENT)


def test_upload_an_avatar(client, data_dir):
    response = upload(client, name="  Oso  ")
    assert response.status_code == 201
    avatar = response.json()
    assert avatar["name"] == "Oso" and avatar["color"] == BROWN and avatar["color_suggested"] is True
    assert avatar["id"].startswith("family-") and avatar["worn_by"] == []
    assert family(client) == [avatar]
    assert client.get(avatar["image_url"]).content == PNG
    saved = yaml.safe_load(config_path(data_dir).read_text())["avatars"]
    assert [a["name"] for a in saved] == ["Oso"]
    assert (data_dir / "avatars" / saved[0]["image"]).read_bytes() == PNG
    assert upload(client, WEBP, name="Gato").status_code == 201


def test_what_is_not_an_avatar(client):
    assert upload(client, JPEG).status_code == 415  # no transparent background
    assert upload(client, b"<svg/>").status_code == 415
    assert upload(client, PNG + b"\0" * (2 * 1024 * 1024)).status_code == 413
    assert upload(client, color="brown").status_code == 422
    assert upload(client, name="  ").status_code == 422
    assert upload(client, headers={}).status_code == 401
    assert family(client) == []


def test_a_child_wears_it_and_takes_its_colour(client):
    avatar = upload(client).json()
    bea = wear(client, avatar["id"]).json()
    assert bea["color"] == BROWN
    assert wear(client, avatar["id"], "Alex").status_code == 409  # one child each
    assert family(client)[0]["worn_by"] == ["Bea"]
    presets = client.get("/api/avatars").json()["presets"]
    assert all(p["worn_by"] == [] for p in presets)
    # A new colour is the child's too, with its tones worked out
    response = client.patch(f"/api/avatars/{avatar['id']}", json={"color": "#3366CC", "color_suggested": False},
                            headers=PARENT)
    assert response.json()["color"] == "#3366cc"
    assert client.get("/api/children").json()[0]["color"] == "#3366cc"
    colors = client.get(f"/api/children/{bea['id']}/today").json()["colors"]
    assert colors["color"] == "#3366cc" and colors["soft"] != colors["strong"] != "#3366cc"


def test_rename_and_log(client):
    avatar = upload(client).json()
    assert client.patch(f"/api/avatars/{avatar['id']}", json={"name": "Osito"}, headers=PARENT).json()["name"] == "Osito"
    assert client.patch(f"/api/avatars/{avatar['id']}", json={"name": " "}, headers=PARENT).status_code == 422
    assert client.patch(f"/api/avatars/{avatar['id']}", json={"name": "X"}).status_code == 401
    texts = [e["description"] for e in client.get("/api/events", headers=PARENT).json()["latest"]]
    assert "Subiste el avatar «Oso»" in texts and "Cambiaste el avatar «Osito» · nombre: Osito" in texts


def test_a_new_picture_brings_its_colour_only_if_it_was_suggested(client, data_dir):
    avatar = upload(client).json()
    url = f"/api/avatars/{avatar['id']}/picture"
    changed = client.put(url, params={"color": "#112233"}, content=WEBP, headers=PARENT).json()
    assert changed["color"] == "#112233" and changed["image_url"] != avatar["image_url"]
    assert client.get(changed["image_url"]).content == WEBP
    assert len(list((data_dir / "avatars").iterdir())) == 1  # the old file went away
    client.patch(f"/api/avatars/{avatar['id']}", json={"color": "#445566", "color_suggested": False}, headers=PARENT)
    kept = client.put(url, params={"color": "#778899"}, content=PNG, headers=PARENT).json()
    assert kept["color"] == "#445566"


def test_delete_only_what_nobody_wears(client, data_dir):
    avatar = upload(client).json()
    bea = wear(client, avatar["id"]).json()
    assert client.delete(f"/api/avatars/{avatar['id']}", headers=PARENT).status_code == 409
    client.put(f"/api/children/{bea['id']}", json={"name": "Bea", "preset": "fox"}, headers=PARENT)
    assert client.delete(f"/api/avatars/{avatar['id']}", headers=PARENT).status_code == 204
    assert family(client) == [] and list((data_dir / "avatars").iterdir()) == []
    assert client.get(avatar["image_url"]).status_code == 404


def test_a_child_goes_and_their_avatar_stays(client):
    avatar = upload(client).json()
    bea = wear(client, avatar["id"]).json()
    client.delete(f"/api/children/{bea['id']}", headers=PARENT)
    assert family(client)[0]["worn_by"] == []


def test_avatars_in_the_backup(client):
    upload(client)
    copy = client.get("/api/backup", headers=PARENT).content
    assert any(n.startswith("avatars/") for n in zipfile.ZipFile(io.BytesIO(copy)).namelist())


def test_migration_17_to_18():
    assert upgrade({"version": 17, "children": []})["avatars"] == []


def test_tones_of_any_colour():
    for entry in avatars.PALETTE:  # hand-picked ones stay
        assert avatars.tones(entry["color"])["soft"] == entry["soft"]
    yellow = avatars.tones("#ffe14d")
    assert yellow["on"] == "#1a1b21"  # a light colour: a dark ✓
    navy = avatars.tones("#1d2b6b")
    assert navy["on"] == "#ffffff" and navy["soft"].startswith("#") and len(navy["strong"]) == 7
