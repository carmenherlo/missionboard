import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage.config_store import config_path
from tests.conftest import PARENT

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
ALL_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def create_child(client, name="Bea", preset="unicorn"):
    body = {"name": name, "preset": preset}
    return client.post("/api/children", json=body, headers=PARENT).json()


def create_mission(client, name="Despegue", **fields):
    return client.post("/api/missions", json={"name": name, **fields}, headers=PARENT)


def patch(client, mission_id, **fields):
    return client.patch(f"/api/missions/{mission_id}", json=fields, headers=PARENT)


def add_task(client, mission_id, text):
    return client.post(f"/api/missions/{mission_id}/tasks", json={"text": text}, headers=PARENT)


def add_step(client, mission_id, task_id, text):
    return client.post(f"/api/missions/{mission_id}/tasks/{task_id}/steps", json={"text": text}, headers=PARENT)


def upload(client, path, data=JPEG, content_type="image/jpeg"):
    return client.put(path, content=data, headers={**PARENT, "Content-Type": content_type})


def saved(data_dir):
    return yaml.safe_load(config_path(data_dir).read_text())


def photo_files(data_dir):
    folder = data_dir / "photos"
    return sorted(p.name for p in folder.iterdir()) if folder.exists() else []


@pytest.fixture
def bea(client):
    return create_child(client)


@pytest.fixture
def mission(client):
    return create_mission(client).json()


@pytest.fixture
def aseo(client, mission):
    """A task with two steps."""
    task = add_task(client, mission["id"], "Aseo").json()["tasks"][0]
    add_step(client, mission["id"], task["id"], "Dientes")
    add_step(client, mission["id"], task["id"], "Cara")
    return client.get(f"/api/missions/{mission['id']}").json()["tasks"][0]


# ---------- missions ----------


def test_new_mission_defaults(client, data_dir):
    response = create_mission(client, name="  Zeta  ")
    assert response.status_code == 201
    mission = response.json()
    assert mission["name"] == "Zeta"
    assert "child_id" not in mission
    assert mission["days"] == ALL_DAYS
    assert mission["schedule"] is None
    assert mission["tasks"] == [] and mission["off"] == {}
    assert mission["image"] is None and mission["image_url"] is None
    assert saved(data_dir)["missions"][0]["id"] == mission["id"]


def test_new_mission_with_library_image(client):
    mission = create_mission(client, image="fluent/rocket").json()
    assert mission["image"] == "fluent/rocket"
    assert mission["image_url"] == "static/libraries/fluent/rocket.svg"


@pytest.mark.parametrize("image", ["fluent/nope", "photo/x.jpg", "other/rocket"])
def test_new_mission_rejects_unknown_image(client, image):
    assert create_mission(client, image=image).status_code == 422


@pytest.mark.parametrize("name", ["", "   ", "x" * 41])
def test_invalid_mission_name(client, name):
    assert create_mission(client, name=name).status_code == 422


@pytest.mark.parametrize("method, path", [
    ("post", "/api/missions"),
    ("put", "/api/missions/order"),
    ("patch", "/api/missions/x"),
    ("delete", "/api/missions/x"),
    ("put", "/api/missions/x/photo"),
    ("post", "/api/missions/x/tasks"),
    ("put", "/api/missions/x/tasks/order"),
    ("patch", "/api/missions/x/tasks/y"),
    ("delete", "/api/missions/x/tasks/y"),
    ("put", "/api/missions/x/tasks/y/photo"),
    ("post", "/api/missions/x/tasks/y/steps"),
    ("patch", "/api/missions/x/steps/y"),
    ("delete", "/api/missions/x/steps/y"),
    ("put", "/api/missions/x/steps/y/place"),
    ("put", "/api/missions/x/steps/y/photo"),
    ("put", "/api/missions/x/children/y/items/z"),
])
def test_writes_require_parent_code(client, method, path):
    kwargs = {} if method == "delete" else {"json": {}}
    assert getattr(client, method)(path, **kwargs).status_code == 401


def test_one_list_for_the_family_in_order(client, data_dir):
    a, b, c = (create_mission(client, name=n).json() for n in "ABC")
    assert [m["name"] for m in client.get("/api/missions").json()] == ["A", "B", "C"]
    response = client.put("/api/missions/order", json={"ids": [c["id"], a["id"], b["id"]]}, headers=PARENT)
    assert [m["name"] for m in response.json()] == ["C", "A", "B"]
    assert [m["name"] for m in saved(data_dir)["missions"]] == ["C", "A", "B"]


@pytest.mark.parametrize("ids", [[], ["nope"]])
def test_reorder_needs_every_mission_once(client, mission, ids):
    assert client.put("/api/missions/order", json={"ids": ids}, headers=PARENT).status_code == 422
    assert client.put("/api/missions/order", json={"ids": [mission["id"]] * 2}, headers=PARENT).status_code == 422


def test_patch_changes_only_sent_fields(client, mission):
    patched = patch(client, mission["id"], name="Otra").json()
    assert patched["name"] == "Otra" and patched["days"] == ALL_DAYS


def test_days_are_stored_in_week_order(client, mission):
    assert patch(client, mission["id"], days=["sun", "mon", "sun"]).json()["days"] == ["mon", "sun"]


@pytest.mark.parametrize("days", [[], ["monday"]])
def test_invalid_days(client, mission, days):
    assert patch(client, mission["id"], days=days).status_code == 422


def test_schedule(client, mission):
    schedule = {"start": "07:00", "end": "09:00"}
    assert patch(client, mission["id"], schedule=schedule).json()["schedule"] == schedule
    assert patch(client, mission["id"], name="Otra").json()["schedule"] == schedule  # untouched
    assert patch(client, mission["id"], schedule=None).json()["schedule"] is None
    only_start = {"start": "07:00"}
    assert patch(client, mission["id"], schedule=only_start).json()["schedule"] == {"start": "07:00", "end": None}


@pytest.mark.parametrize("schedule", [{"start": "25:00"}, {"start": "07:00", "end": "07:00"}, {"start": "7:00"}])
def test_invalid_schedule(client, mission, schedule):
    assert patch(client, mission["id"], schedule=schedule).status_code == 422


def test_a_colour_of_the_palette(client, mission):
    first, second = mission, create_mission(client, name="Otra").json()
    assert first["color"] != second["color"]  # each one starts with one no mission has
    changed = patch(client, first["id"], color="#e77300").json()
    assert changed["color"] == "#e77300" and changed["colors"]["soft"] == "#ffdcc7"
    assert patch(client, first["id"], color="#123456").status_code == 422
    assert patch(client, first["id"], color="#f2a36c").status_code == 422  # peach: only for rings
    assert "#f2a36c" not in client.get("/api/avatars").json()["mission_colors"]


def test_patch_image(client, mission):
    assert patch(client, mission["id"], image="fluent/rocket").json()["image_url"].endswith("rocket.svg")
    assert patch(client, mission["id"], image=None).json()["image_url"] is None
    assert patch(client, mission["id"], image="fluent/nope").status_code == 422


def test_missing_mission(client):
    assert client.get("/api/missions/nope").status_code == 404
    assert patch(client, "nope", name="x").status_code == 404
    assert client.delete("/api/missions/nope", headers=PARENT).status_code == 404


def test_delete_mission(client, mission, data_dir):
    assert client.delete(f"/api/missions/{mission['id']}", headers=PARENT).status_code == 204
    assert client.get(f"/api/missions/{mission['id']}").status_code == 404
    assert saved(data_dir)["missions"] == []


def test_mission_photo(client, mission, data_dir):
    updated = upload(client, f"/api/missions/{mission['id']}/photo").json()
    assert updated["image"].startswith("photo/") and updated["image_url"].startswith("api/photos/")
    assert client.get(updated["image_url"]).content == JPEG
    assert len(photo_files(data_dir)) == 1


def test_replacing_a_photo_removes_the_old_file(client, mission, data_dir):
    upload(client, f"/api/missions/{mission['id']}/photo")
    upload(client, f"/api/missions/{mission['id']}/photo", data=PNG, content_type="image/png")
    assert len(photo_files(data_dir)) == 1
    patch(client, mission["id"], image=None)
    assert photo_files(data_dir) == []


def test_keeping_the_same_photo(client, mission, data_dir):
    image = upload(client, f"/api/missions/{mission['id']}/photo").json()["image"]
    assert patch(client, mission["id"], image=image).json()["image"] == image
    assert len(photo_files(data_dir)) == 1


@pytest.mark.parametrize("data, content_type, status", [
    (b"not an image", "image/jpeg", 422), (JPEG, "image/gif", 415), (b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024), "image/jpeg", 413),
])
def test_invalid_photo(client, mission, data, content_type, status):
    assert upload(client, f"/api/missions/{mission['id']}/photo", data, content_type).status_code == status


def test_photo_endpoint_only_serves_photos(client):
    assert client.get("/api/photos/missing.jpg").status_code == 404
    assert client.get("/api/photos/..%2Fconfig.yaml").status_code == 404


# ---------- tasks and steps ----------


def test_tasks_with_their_steps(client, mission, aseo, data_dir):
    assert aseo["text"] == "Aseo" and aseo["days"] is None
    assert [s["text"] for s in aseo["steps"]] == ["Dientes", "Cara"]
    assert [s["text"] for s in saved(data_dir)["missions"][0]["tasks"][0]["steps"]] == ["Dientes", "Cara"]
    assert add_task(client, mission["id"], "x" * 61).status_code == 422
    assert add_task(client, mission["id"], "  ").status_code == 422
    assert add_step(client, mission["id"], "nope", "Otra").status_code == 404
    assert add_step(client, mission["id"], aseo["id"], "x" * 61).status_code == 422


def test_update_a_task_and_a_step(client, mission, aseo):
    url = f"/api/missions/{mission['id']}"
    task = client.patch(f"{url}/tasks/{aseo['id']}", json={"text": "Lavarse", "image": "fluent/soap"},
                        headers=PARENT).json()["tasks"][0]
    assert task["text"] == "Lavarse" and task["image_url"].endswith("soap.svg")
    step = aseo["steps"][0]
    updated = client.patch(f"{url}/steps/{step['id']}", json={"text": "Boca"}, headers=PARENT).json()
    assert updated["tasks"][0]["steps"][0]["text"] == "Boca"
    assert client.patch(f"{url}/steps/nope", json={"text": "x"}, headers=PARENT).status_code == 404
    assert client.patch(f"{url}/tasks/nope", json={"text": "x"}, headers=PARENT).status_code == 404


def test_reorder_tasks(client, mission):
    add_task(client, mission["id"], "Uno")
    tasks = add_task(client, mission["id"], "Dos").json()["tasks"]
    ids = [tasks[1]["id"], tasks[0]["id"]]
    url = f"/api/missions/{mission['id']}/tasks/order"
    assert [t["text"] for t in client.put(url, json={"ids": ids}, headers=PARENT).json()["tasks"]] == ["Dos", "Uno"]
    assert client.put(url, json={"ids": ids[:1]}, headers=PARENT).status_code == 422


def test_a_step_moves_within_its_task_and_to_another(client, mission, aseo):
    other = add_task(client, mission["id"], "Vestirse").json()["tasks"][1]
    url = f"/api/missions/{mission['id']}/steps"
    cara = aseo["steps"][1]["id"]
    moved = client.put(f"{url}/{cara}/place", json={"task_id": aseo["id"], "position": 0}, headers=PARENT).json()
    assert [s["text"] for s in moved["tasks"][0]["steps"]] == ["Cara", "Dientes"]
    moved = client.put(f"{url}/{cara}/place", json={"task_id": other["id"], "position": 0}, headers=PARENT).json()
    assert [s["text"] for s in moved["tasks"][0]["steps"]] == ["Dientes"]
    assert [s["text"] for s in moved["tasks"][1]["steps"]] == ["Cara"]
    assert client.put(f"{url}/{cara}/place", json={"task_id": "nope", "position": 0}, headers=PARENT).status_code == 404
    assert client.put(f"{url}/nope/place", json={"task_id": other["id"], "position": 0}, headers=PARENT).status_code == 404


def test_deleting_cleans_up_photos(client, mission, aseo, data_dir):
    url = f"/api/missions/{mission['id']}"
    step = aseo["steps"][0]
    upload(client, f"{url}/steps/{step['id']}/photo")
    upload(client, f"{url}/steps/{aseo['steps'][1]['id']}/photo")
    upload(client, f"{url}/tasks/{aseo['id']}/photo")
    assert len(photo_files(data_dir)) == 3
    client.delete(f"{url}/steps/{step['id']}", headers=PARENT)
    assert len(photo_files(data_dir)) == 2
    assert client.delete(f"{url}/tasks/{aseo['id']}", headers=PARENT).json()["tasks"] == []
    assert photo_files(data_dir) == []


def test_deleting_a_mission_removes_its_photos(client, mission, aseo, data_dir):
    url = f"/api/missions/{mission['id']}"
    upload(client, f"{url}/photo")
    upload(client, f"{url}/tasks/{aseo['id']}/photo")
    upload(client, f"{url}/steps/{aseo['steps'][0]['id']}/photo")
    client.delete(url, headers=PARENT)
    assert photo_files(data_dir) == []


# ---------- each child, with what they have on ----------


def test_everything_is_on_for_everyone_by_default(client, mission, aseo, bea):
    alex = create_child(client, name="Alex", preset="dinosaur")
    found = client.get(f"/api/missions/{mission['id']}").json()
    assert found["children"] == [
        {"id": bea["id"], "active": 3, "total": 3},
        {"id": alex["id"], "active": 3, "total": 3},
    ]


def test_switch_off_and_on_for_one_child(client, mission, aseo, bea, data_dir):
    alex = create_child(client, name="Alex", preset="dinosaur")
    url = f"/api/missions/{mission['id']}/children/{alex['id']}/items"
    step = aseo["steps"][0]["id"]
    off = client.put(f"{url}/{step}", json={"active": False}, headers=PARENT).json()
    assert off["off"] == {alex["id"]: [step]}
    assert off["children"][1]["active"] == 2 and off["children"][0]["active"] == 3
    assert saved(data_dir)["missions"][0]["off"] == {alex["id"]: [step]}
    assert client.put(f"{url}/{step}", json={"active": True}, headers=PARENT).json()["off"] == {}
    assert client.put(f"{url}/nope", json={"active": False}, headers=PARENT).status_code == 404
    gone = f"/api/missions/{mission['id']}/children/nope/items/{step}"
    assert client.put(gone, json={"active": False}, headers=PARENT).status_code == 404


def test_new_things_are_on_for_everyone(client, mission, aseo, bea):
    url = f"/api/missions/{mission['id']}/children/{bea['id']}/items/{aseo['id']}"
    client.put(url, json={"active": False}, headers=PARENT)
    added = add_step(client, mission["id"], aseo["id"], "Peine").json()
    assert added["children"][0] == {"id": bea["id"], "active": 3, "total": 4}


def test_what_is_deleted_or_whoever_leaves_is_forgotten(client, mission, aseo, bea):
    alex = create_child(client, name="Alex", preset="dinosaur")
    base = f"/api/missions/{mission['id']}"
    step = aseo["steps"][0]["id"]
    client.put(f"{base}/children/{bea['id']}/items/{step}", json={"active": False}, headers=PARENT)
    client.put(f"{base}/children/{alex['id']}/items/{aseo['id']}", json={"active": False}, headers=PARENT)
    assert client.delete(f"{base}/steps/{step}", headers=PARENT).json()["off"] == {alex["id"]: [aseo["id"]]}
    assert [c["id"] for c in client.get(base).json()["children"]] == [bea["id"], alex["id"]]
    client.delete(f"/api/children/{alex['id']}", headers=PARENT)
    assert client.get(base).json()["off"] == {}
    assert client.get(base).status_code == 200  # the mission stays: it is the family's


# ---------- suggested images ----------


def test_new_mission_gets_a_suggested_image(client):
    mission = create_mission(client, name="Cepillarse los dientes").json()
    assert mission["image"] == "fluent/toothbrush" and mission["image_suggested"] is True


def test_chosen_image_is_not_marked_as_suggested(client):
    mission = create_mission(client, name="Dientes", image="fluent/rocket").json()
    assert mission["image"] == "fluent/rocket" and mission["image_suggested"] is False


def test_new_tasks_and_steps_get_a_suggested_image(client, mission):
    task = add_task(client, mission["id"], "Lavarse los dientes").json()["tasks"][0]
    assert task["image"] == "fluent/toothbrush" and task["image_suggested"] is True
    step = add_step(client, mission["id"], task["id"], "Cepillo de dientes").json()["tasks"][0]["steps"][0]
    assert step["image"] == "fluent/toothbrush" and step["image_suggested"] is True


def test_no_suggestion_when_nothing_fits(client, mission):
    task = add_task(client, mission["id"], "xyzzy").json()["tasks"][0]
    assert task["image"] is None and task["image_suggested"] is False


def test_touching_the_image_clears_the_mark(client, mission):
    task = add_task(client, mission["id"], "Lavarse los dientes").json()["tasks"][0]
    url = f"/api/missions/{mission['id']}/tasks/{task['id']}"
    updated = client.patch(url, json={"image": task["image"]}, headers=PARENT).json()["tasks"][0]
    assert updated["image_suggested"] is False


def test_a_text_change_keeps_the_suggestion(client, mission):
    task = add_task(client, mission["id"], "Lavarse los dientes").json()["tasks"][0]
    url = f"/api/missions/{mission['id']}/tasks/{task['id']}"
    assert client.patch(url, json={"text": "Dientes"}, headers=PARENT).json()["tasks"][0]["image_suggested"] is True


def test_a_photo_clears_the_mark(client, mission):
    task = add_task(client, mission["id"], "Lavarse los dientes").json()["tasks"][0]
    updated = upload(client, f"/api/missions/{mission['id']}/tasks/{task['id']}/photo").json()["tasks"][0]
    assert updated["image_suggested"] is False


def test_image_of_a_removed_library_shows_nothing(tmp_path):
    with TestClient(create_app(tmp_path, libraries=[])) as client:
        mission = create_mission(client, image=None).json()
        assert mission["image_url"] is None
