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
    body = {"name": name, "avatar_type": "preset", "preset": preset}
    return client.post("/api/children", json=body, headers=PARENT).json()


def create_mission(client, child_id, name="Despegue", **fields):
    return client.post(
        f"/api/children/{child_id}/missions", json={"name": name, **fields}, headers=PARENT
    )


def patch(client, mission_id, **fields):
    return client.patch(f"/api/missions/{mission_id}", json=fields, headers=PARENT)


def add_step(client, mission_id, text):
    return client.post(f"/api/missions/{mission_id}/steps", json={"text": text}, headers=PARENT)


def upload(client, path, data=JPEG, content_type="image/jpeg"):
    return client.put(path, content=data, headers={**PARENT, "Content-Type": content_type})


def saved(data_dir):
    return yaml.safe_load(config_path(data_dir).read_text())


@pytest.fixture
def bea(client):
    return create_child(client)


@pytest.fixture
def mission(client, bea):
    return create_mission(client, bea["id"]).json()


def photo_files(data_dir):
    folder = data_dir / "photos"
    return sorted(p.name for p in folder.iterdir()) if folder.exists() else []


# ---------- missions ----------


def test_new_mission_defaults(client, bea, data_dir):
    response = create_mission(client, bea["id"], name="  Despegue  ")
    assert response.status_code == 201
    mission = response.json()
    assert mission["name"] == "Despegue"
    assert mission["child_id"] == bea["id"]
    assert mission["days"] == ALL_DAYS
    assert mission["schedule"] is None
    assert mission["steps"] == []
    assert mission["image"] is None and mission["image_url"] is None
    assert saved(data_dir)["missions"][0]["id"] == mission["id"]


def test_new_mission_with_library_image(client, bea):
    mission = create_mission(client, bea["id"], image="fluent/rocket").json()
    assert mission["image"] == "fluent/rocket"
    assert mission["image_url"] == "/static/libraries/fluent/rocket.svg"
    assert client.get(mission["image_url"]).status_code == 200


@pytest.mark.parametrize("image", ["fluent/not-an-image", "other/rocket", "photo/x.jpg"])
def test_new_mission_rejects_unknown_image(client, bea, image):
    assert create_mission(client, bea["id"], image=image).status_code == 422


@pytest.mark.parametrize("name", ["", "   ", "x" * 41])
def test_invalid_mission_name(client, bea, name):
    assert create_mission(client, bea["id"], name=name).status_code == 422


def test_mission_for_missing_child(client):
    assert create_mission(client, "missing").status_code == 404
    assert client.get("/api/children/missing/missions").status_code == 404


@pytest.mark.parametrize(
    "method, path",
    [
        ("post", "/api/children/x/missions"),
        ("put", "/api/children/x/missions/order"),
        ("patch", "/api/missions/x"),
        ("delete", "/api/missions/x"),
        ("put", "/api/missions/x/photo"),
        ("post", "/api/missions/x/steps"),
        ("put", "/api/missions/x/steps/order"),
        ("patch", "/api/missions/x/steps/y"),
        ("delete", "/api/missions/x/steps/y"),
        ("put", "/api/missions/x/steps/y/photo"),
    ],
)
def test_writes_require_parent_code(client, method, path):
    assert client.request(method, path, json={}).status_code == 401


def test_missions_are_listed_per_child_in_order(client, bea):
    alex = create_child(client, "Alex", "dinosaur")
    for name in ("Despegue", "Aterrizaje"):
        create_mission(client, bea["id"], name=name)
    create_mission(client, alex["id"], name="Alunizaje")
    assert [m["name"] for m in client.get(f"/api/children/{bea['id']}/missions").json()] == [
        "Despegue",
        "Aterrizaje",
    ]
    assert [m["name"] for m in client.get(f"/api/children/{alex['id']}/missions").json()] == [
        "Alunizaje"
    ]


def test_reorder_missions_keeps_other_children(client, bea, data_dir):
    alex = create_child(client, "Alex", "dinosaur")
    a = create_mission(client, bea["id"], name="A").json()
    x = create_mission(client, alex["id"], name="X").json()
    b = create_mission(client, bea["id"], name="B").json()
    c = create_mission(client, bea["id"], name="C").json()

    response = client.put(
        f"/api/children/{bea['id']}/missions/order", json={"ids": [c["id"], a["id"], b["id"]]},
        headers=PARENT,
    )
    assert response.status_code == 200
    assert [m["name"] for m in response.json()] == ["C", "A", "B"]
    assert [m["name"] for m in saved(data_dir)["missions"]] == ["C", "X", "A", "B"]
    assert client.get(f"/api/children/{alex['id']}/missions").json()[0]["id"] == x["id"]


@pytest.mark.parametrize("ids", [[], ["a"], ["a", "a"]])
def test_reorder_missions_needs_every_mission_once(client, bea, ids):
    a = create_mission(client, bea["id"], name="A").json()
    create_mission(client, bea["id"], name="B")
    ids = [a["id"] if i == "a" else i for i in ids]
    response = client.put(f"/api/children/{bea['id']}/missions/order", json={"ids": ids}, headers=PARENT)
    assert response.status_code == 422


def test_patch_changes_only_sent_fields(client, mission):
    patch(client, mission["id"], days=["mon", "wed"])
    response = patch(client, mission["id"], name="Despegue ya")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Despegue ya"
    assert body["days"] == ["mon", "wed"]


def test_days_are_stored_in_week_order(client, mission):
    assert patch(client, mission["id"], days=["fri", "mon", "fri"]).json()["days"] == ["mon", "fri"]


@pytest.mark.parametrize("days", [[], ["monday"], None])
def test_invalid_days(client, mission, days):
    response = patch(client, mission["id"], days=days)
    if days is None:  # null is ignored: days can't be removed
        assert response.json()["days"] == ALL_DAYS
    else:
        assert response.status_code == 422


def test_schedule(client, mission):
    body = patch(client, mission["id"], schedule={"start": "07:00", "end": "08:15"}).json()
    assert body["schedule"] == {"start": "07:00", "end": "08:15"}
    body = patch(client, mission["id"], schedule={"start": "16:00"}).json()
    assert body["schedule"] == {"start": "16:00", "end": None}
    assert patch(client, mission["id"], schedule=None).json()["schedule"] is None


@pytest.mark.parametrize(
    "schedule",
    [{"start": "7:00"}, {"start": "24:00"}, {"start": "08:00", "end": "07:00"},
     {"start": "08:00", "end": "08:00"}, {"end": "08:00"}],
)
def test_invalid_schedule(client, mission, schedule):
    assert patch(client, mission["id"], schedule=schedule).status_code == 422


def test_patch_image(client, mission):
    assert patch(client, mission["id"], image="fluent/bed").json()["image_url"].endswith("/bed.svg")
    assert patch(client, mission["id"], image=None).json()["image"] is None
    assert patch(client, mission["id"], image="fluent/nope").status_code == 422


def test_missing_mission(client):
    assert client.get("/api/missions/missing").status_code == 404
    assert patch(client, "missing", name="X").status_code == 404
    assert client.delete("/api/missions/missing", headers=PARENT).status_code == 404


def test_delete_mission(client, bea, mission, data_dir):
    assert client.delete(f"/api/missions/{mission['id']}", headers=PARENT).status_code == 204
    assert client.get(f"/api/children/{bea['id']}/missions").json() == []
    assert saved(data_dir)["missions"] == []


# ---------- mission photo ----------


def test_mission_photo(client, mission, data_dir):
    response = upload(client, f"/api/missions/{mission['id']}/photo")
    assert response.status_code == 200
    body = response.json()
    assert body["image"].startswith("photo/")
    assert client.get(body["image_url"]).content == JPEG
    assert len(photo_files(data_dir)) == 1


def test_replacing_mission_photo_removes_old_file(client, mission, data_dir):
    upload(client, f"/api/missions/{mission['id']}/photo")
    second = upload(client, f"/api/missions/{mission['id']}/photo", PNG, "image/png").json()
    assert photo_files(data_dir) == [second["image"].removeprefix("photo/")]
    patch(client, mission["id"], image="fluent/rocket")
    assert photo_files(data_dir) == []


def test_keeping_the_same_photo(client, mission, data_dir):
    photo = upload(client, f"/api/missions/{mission['id']}/photo").json()["image"]
    assert patch(client, mission["id"], image=photo).status_code == 200
    assert len(photo_files(data_dir)) == 1


@pytest.mark.parametrize(
    "data, content_type, status",
    [(JPEG, "image/gif", 415), (PNG, "image/jpeg", 422), (b"", "image/png", 422)],
)
def test_invalid_mission_photo(client, mission, data, content_type, status):
    assert upload(client, f"/api/missions/{mission['id']}/photo", data, content_type).status_code == status


def test_photo_endpoint_only_serves_photos(client):
    assert client.get("/api/photos/missing.jpg").status_code == 404
    assert client.get("/api/photos/..%2Fconfig.yaml").status_code == 404


# ---------- steps ----------


def test_add_steps(client, mission, data_dir):
    add_step(client, mission["id"], "Hacer la cama")
    response = add_step(client, mission["id"], "  Lleva el plato al fregadero  ")
    assert response.status_code == 201
    steps = response.json()["steps"]
    assert [s["text"] for s in steps] == ["Hacer la cama", "Lleva el plato al fregadero"]
    assert steps[0]["id"] != steps[1]["id"]
    assert steps[0]["image"] is None and steps[0]["image_url"] is None
    assert len(saved(data_dir)["missions"][0]["steps"]) == 2


@pytest.mark.parametrize("text", ["", "   ", "x" * 61])
def test_invalid_step_text(client, mission, text):
    assert add_step(client, mission["id"], text).status_code == 422


def test_step_text_limit(client, mission):
    assert add_step(client, mission["id"], "x" * 60).status_code == 201


def test_update_step(client, mission):
    step = add_step(client, mission["id"], "Desayunar").json()["steps"][0]
    url = f"/api/missions/{mission['id']}/steps/{step['id']}"
    body = client.patch(url, json={"image": "fluent/bowl-with-spoon"}, headers=PARENT).json()
    assert body["steps"][0]["text"] == "Desayunar"
    assert body["steps"][0]["image_url"].endswith("/bowl-with-spoon.svg")
    body = client.patch(url, json={"text": "Desayunar todo"}, headers=PARENT).json()
    assert body["steps"][0]["image"] == "fluent/bowl-with-spoon"
    assert body["steps"][0]["text"] == "Desayunar todo"
    assert client.patch(url, json={"image": "fluent/nope"}, headers=PARENT).status_code == 422
    assert client.patch(url, json={"text": ""}, headers=PARENT).status_code == 422


def test_missing_step(client, mission):
    url = f"/api/missions/{mission['id']}/steps/missing"
    assert client.patch(url, json={"text": "x"}, headers=PARENT).status_code == 404
    assert client.delete(url, headers=PARENT).status_code == 404


def test_reorder_and_delete_steps(client, mission):
    for text in ("A", "B", "C"):
        steps = add_step(client, mission["id"], text).json()["steps"]
    a, b, c = (s["id"] for s in steps)
    url = f"/api/missions/{mission['id']}/steps"
    body = client.put(f"{url}/order", json={"ids": [c, a, b]}, headers=PARENT).json()
    assert [s["text"] for s in body["steps"]] == ["C", "A", "B"]
    assert client.put(f"{url}/order", json={"ids": [c, a]}, headers=PARENT).status_code == 422
    body = client.delete(f"{url}/{a}", headers=PARENT).json()
    assert [s["text"] for s in body["steps"]] == ["C", "B"]


def test_step_photos_are_cleaned_up(client, mission, data_dir):
    step = add_step(client, mission["id"], "Desayunar").json()["steps"][0]
    url = f"/api/missions/{mission['id']}/steps/{step['id']}"
    body = upload(client, f"{url}/photo").json()
    assert client.get(body["steps"][0]["image_url"]).content == JPEG
    upload(client, f"{url}/photo", PNG, "image/png")
    assert len(photo_files(data_dir)) == 1
    client.delete(url, headers=PARENT)
    assert photo_files(data_dir) == []


def test_deleting_mission_removes_its_photos(client, mission, data_dir):
    step = add_step(client, mission["id"], "Desayunar").json()["steps"][0]
    upload(client, f"/api/missions/{mission['id']}/photo")
    upload(client, f"/api/missions/{mission['id']}/steps/{step['id']}/photo")
    assert len(photo_files(data_dir)) == 2
    client.delete(f"/api/missions/{mission['id']}", headers=PARENT)
    assert photo_files(data_dir) == []


# ---------- children ----------


def test_deleting_child_removes_their_missions_and_photos(client, bea, data_dir):
    alex = create_child(client, "Alex", "dinosaur")
    mine = create_mission(client, bea["id"]).json()
    create_mission(client, alex["id"], name="De Alex")
    upload(client, f"/api/missions/{mine['id']}/photo")

    assert client.delete(f"/api/children/{bea['id']}", headers=PARENT).status_code == 204
    assert [m["name"] for m in saved(data_dir)["missions"]] == ["De Alex"]
    assert photo_files(data_dir) == []


# ---------- libraries ----------


def test_image_of_removed_library_shows_nothing(tmp_path):
    data_dir = tmp_path / "data"
    with TestClient(create_app(data_dir)) as client:
        child = create_child(client)
        mission = create_mission(client, child["id"], image="fluent/rocket").json()
    with TestClient(create_app(data_dir, libraries=[])) as client:
        body = client.get(f"/api/missions/{mission['id']}").json()
    assert body["image"] == "fluent/rocket"
    assert body["image_url"] is None
