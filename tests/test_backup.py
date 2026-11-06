import io
import json
import zipfile

import yaml

from app.storage.config_store import config_path
from tests.conftest import PARENT
from tests.test_missions import JPEG, create_child, create_mission, upload


def download(client):
    response = client.get("/api/backup", headers=PARENT)
    assert response.status_code == 200 and response.headers["content-type"] == "application/zip"
    return response.content


def restore(client, data):
    return client.post("/api/backup/restore", content=data, headers={**PARENT, "Content-Type": "application/zip"})


def zipped(files: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buffer.getvalue()


def test_a_copy_has_everything(client):
    bea = create_child(client)
    mission = create_mission(client, bea["id"]).json()
    upload(client, f"/api/missions/{mission['id']}/photo")
    names = zipfile.ZipFile(io.BytesIO(download(client))).namelist()
    assert {"config.yaml", "missionboard.db", "missionboard-backup.json"} <= set(names)
    assert any(n.startswith("photos/") for n in names)
    manifest = json.loads(zipfile.ZipFile(io.BytesIO(download(client))).read("missionboard-backup.json"))
    assert manifest["app"] == "missionboard" and manifest["config_version"] >= 14


def test_put_a_copy_back(client, data_dir):
    bea = create_child(client)
    create_mission(client, bea["id"], name="Despegue")
    copy = download(client)
    client.delete(f"/api/children/{bea['id']}", headers=PARENT)
    create_child(client, name="Alex", preset="dinosaur")
    response = restore(client, copy)
    assert response.status_code == 200
    assert [c["name"] for c in client.get("/api/children").json()] == ["Bea"]
    assert [m["name"] for m in client.get(f"/api/children/{bea['id']}/missions").json()] == ["Despegue"]
    # What there was is kept, in case
    kept = data_dir / "backups" / response.json()["kept"]
    assert kept.exists() and "config.yaml" in zipfile.ZipFile(kept).namelist()


def test_a_copy_needs_the_parent_code(client):
    assert client.get("/api/backup").status_code == 401
    assert client.post("/api/backup/restore", content=b"x").status_code == 401


def test_what_is_not_a_copy_changes_nothing(client, data_dir):
    create_child(client)
    before = config_path(data_dir).read_text()
    assert restore(client, b"not a zip").status_code == 422
    assert restore(client, zipped({"hello.txt": "hi"})).status_code == 422
    newer = yaml.safe_dump({"version": 999})
    assert restore(client, zipped({"config.yaml": newer, "missionboard-backup.json": "{}"})).status_code == 422
    assert config_path(data_dir).read_text() == before


def test_nothing_outside_its_folders(client, data_dir):
    copy = zipfile.ZipFile(io.BytesIO(download(client)))
    files = {name: copy.read(name) for name in copy.namelist()}
    files["../outside.txt"] = "x"
    files["photos/../../outside2.txt"] = "x"
    files["photos/ok.jpg"] = JPEG
    assert restore(client, zipped(files)).status_code == 200
    assert not (data_dir.parent / "outside.txt").exists() and not (data_dir.parent / "outside2.txt").exists()
    assert (data_dir / "photos" / "ok.jpg").exists()


def test_an_old_copy_is_brought_up_to_date(client):
    old = yaml.safe_dump({"version": 13, "children": [{"id": "c1", "name": "Bea", "avatar_type": "preset",
                                                       "preset": "unicorn", "color": "#9471e7"}]})
    assert restore(client, zipped({"config.yaml": old, "missionboard-backup.json": "{}"})).status_code == 200
    assert [c["name"] for c in client.get("/api/children").json()] == ["Bea"]
