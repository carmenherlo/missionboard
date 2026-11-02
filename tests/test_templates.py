import pytest

from tests.conftest import PARENT
from tests.test_missions import (
    PNG,
    add_step,
    create_child,
    create_mission,
    patch,
    photo_files,
    saved,
    upload,
)

SAMPLES = ["Despegue", "Aterrizaje", "Alunizaje"]


def create_template(client, name="Limpieza", **fields):
    return client.post("/api/templates", json={"name": name, **fields}, headers=PARENT)


def apply(client, template_id, child_ids):
    return client.post(f"/api/templates/{template_id}/apply", json={"child_ids": child_ids}, headers=PARENT)


def save_as_template(client, mission_id):
    return client.post(f"/api/missions/{mission_id}/template", headers=PARENT)


def names(items):
    return [item["name"] for item in items]


@pytest.fixture
def bea(client):
    return create_child(client)


@pytest.fixture
def alex(client):
    return create_child(client, name="Alex", preset="dinosaur")


# ---------- samples and list ----------


def test_a_new_install_has_the_three_samples(client):
    templates = client.get("/api/templates").json()
    assert names(templates) == SAMPLES
    despegue = templates[0]
    assert despegue["child_id"] is None
    assert despegue["days"] == ["mon", "tue", "wed", "thu", "fri"]
    assert despegue["schedule"] is None
    assert despegue["image_url"] == "/static/libraries/fluent/rocket.svg"
    assert [s["text"] for s in despegue["steps"]] == [
        "Hacer la cama", "Vestirse", "Desayunar", "Lavarse los dientes", "Peinarse", "Preparar la mochila",
    ]
    assert despegue["steps"][4]["image"] is None


def test_samples_can_be_deleted_for_good(client, data_dir):
    for template in client.get("/api/templates").json():
        assert client.delete(f"/api/templates/{template['id']}", headers=PARENT).status_code == 204
    assert client.get("/api/templates").json() == []
    assert saved(data_dir)["templates"] == []


# ---------- create and edit ----------


def test_new_template_goes_last_with_mission_defaults(client, data_dir):
    response = create_template(client, name="  Limpieza  ")
    assert response.status_code == 201
    template = response.json()
    assert template["name"] == "Limpieza"
    assert template["child_id"] is None
    assert template["days"] == ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    assert template["steps"] == []
    assert names(client.get("/api/templates").json()) == SAMPLES + ["Limpieza"]
    assert "child_id" not in saved(data_dir)["templates"][-1]


def test_new_template_gets_a_suggested_image(client):
    template = create_template(client, name="Desayuno").json()
    assert template["image"] is not None and template["image_suggested"] is True


def test_templates_are_edited_like_missions(client):
    template = create_template(client).json()
    url = f"/api/templates/{template['id']}"
    assert client.patch(url, json={"name": "Baño", "days": ["sat", "sun"]}, headers=PARENT).status_code == 200
    step = client.post(f"{url}/steps", json={"text": "Ducharse"}, headers=PARENT).json()["steps"][0]
    client.patch(f"{url}/steps/{step['id']}", json={"text": "Ducha"}, headers=PARENT)
    got = client.get(url).json()
    assert got["name"] == "Baño" and got["days"] == ["sat", "sun"]
    assert [s["text"] for s in got["steps"]] == ["Ducha"]


def test_a_mission_id_is_not_a_template(client, bea):
    mission = create_mission(client, bea["id"]).json()
    response = client.get(f"/api/templates/{mission['id']}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Template not found"


@pytest.mark.parametrize("call", [
    lambda c, t: c.post("/api/templates", json={"name": "X"}),
    lambda c, t: c.patch(f"/api/templates/{t}", json={"name": "X"}),
    lambda c, t: c.delete(f"/api/templates/{t}"),
    lambda c, t: c.post(f"/api/templates/{t}/apply", json={"child_ids": []}),
])
def test_changes_need_the_parent_code(client, call):
    assert call(client, "despegue").status_code == 401


# ---------- apply ----------


def test_apply_gives_each_child_a_copy_at_the_end_of_their_route(client, bea, alex):
    first = create_mission(client, bea["id"], name="Primera").json()
    response = apply(client, "despegue", [bea["id"], alex["id"]])
    assert response.status_code == 201
    copies = response.json()
    assert [c["child_id"] for c in copies] == [bea["id"], alex["id"]]
    assert names(copies) == ["Despegue", "Despegue"]
    assert copies[0]["id"] != copies[1]["id"] != "despegue"
    assert copies[0]["steps"][0]["id"] != copies[1]["steps"][0]["id"]
    assert copies[0]["days"] == ["mon", "tue", "wed", "thu", "fri"]
    assert len(copies[0]["steps"]) == 6
    route = client.get(f"/api/children/{bea['id']}/missions").json()
    assert [m["id"] for m in route] == [first["id"], copies[0]["id"]]


def test_apply_keeps_the_name_when_the_child_already_has_it(client, bea):
    create_mission(client, bea["id"], name="Despegue")
    apply(client, "despegue", [bea["id"]])
    assert names(client.get(f"/api/children/{bea['id']}/missions").json()) == ["Despegue", "Despegue"]


def test_template_and_copies_change_independently(client, bea, alex):
    bea_copy, alex_copy = apply(client, "despegue", [bea["id"], alex["id"]]).json()
    client.patch("/api/templates/despegue", json={"name": "Mañana"}, headers=PARENT)
    patch(client, bea_copy["id"], days=["sat"])
    add_step(client, bea_copy["id"], "Abrigarse")
    assert client.get(f"/api/missions/{bea_copy['id']}").json()["name"] == "Despegue"
    assert client.get(f"/api/missions/{alex_copy['id']}").json()["days"] == ["mon", "tue", "wed", "thu", "fri"]
    assert len(client.get(f"/api/missions/{alex_copy['id']}").json()["steps"]) == 6
    template = client.get("/api/templates/despegue").json()
    assert template["days"] == ["mon", "tue", "wed", "thu", "fri"] and len(template["steps"]) == 6


@pytest.mark.parametrize("child_ids, status", [([], 422), (["same", "same"], 422), (["nobody"], 404)])
def test_apply_checks_the_children(client, bea, child_ids, status):
    child_ids = [bea["id"] if c == "same" else c for c in child_ids]
    assert apply(client, "despegue", child_ids).status_code == status
    assert client.get(f"/api/children/{bea['id']}/missions").json() == []


def test_apply_with_one_unknown_child_saves_nothing(client, bea):
    assert apply(client, "despegue", [bea["id"], "nobody"]).status_code == 404
    assert client.get(f"/api/children/{bea['id']}/missions").json() == []


def test_apply_an_unknown_template(client, bea):
    assert apply(client, "nope", [bea["id"]]).status_code == 404


# ---------- save a mission as a template ----------


def test_save_a_mission_as_a_template(client, bea, alex):
    mission = create_mission(client, bea["id"], name="Deberes", image="fluent/books").json()
    patch(client, mission["id"], days=["mon", "wed"], schedule={"start": "17:00", "end": "18:00"})
    add_step(client, mission["id"], "Sacar los libros")
    response = save_as_template(client, mission["id"])
    assert response.status_code == 201
    template = response.json()
    assert template["child_id"] is None and template["id"] != mission["id"]
    assert template["name"] == "Deberes" and template["image"] == "fluent/books"
    assert template["days"] == ["mon", "wed"]
    assert template["schedule"] == {"start": "17:00", "end": "18:00"}
    assert [s["text"] for s in template["steps"]] == ["Sacar los libros"]
    # The way to pass a mission from one child to another
    copy = apply(client, template["id"], [alex["id"]]).json()[0]
    assert copy["name"] == "Deberes" and copy["schedule"] == {"start": "17:00", "end": "18:00"}


def test_saving_with_a_taken_name_numbers_it(client, bea):
    mission = create_mission(client, bea["id"], name="Despegue").json()
    assert save_as_template(client, mission["id"]).json()["name"] == "Despegue (2)"
    assert save_as_template(client, mission["id"]).json()["name"] == "Despegue (3)"


def test_a_numbered_name_still_fits(client, bea):
    long_name = "D" * 40
    mission = create_mission(client, bea["id"], name=long_name).json()
    save_as_template(client, mission["id"])
    second = save_as_template(client, mission["id"]).json()["name"]
    assert second == "D" * 36 + " (2)" and len(second) == 40


def test_save_an_unknown_mission(client):
    assert save_as_template(client, "nope").status_code == 404


# ---------- photos: every copy owns its files ----------


def test_photos_are_copied_and_survive_deleting_the_original(client, bea, alex, data_dir):
    template = create_template(client).json()
    url = f"/api/templates/{template['id']}"
    upload(client, f"{url}/photo", PNG, "image/png")
    step = client.post(f"{url}/steps", json={"text": "Ducharse"}, headers=PARENT).json()["steps"][0]
    upload(client, f"{url}/steps/{step['id']}/photo")
    assert len(photo_files(data_dir)) == 2

    copies = apply(client, template["id"], [bea["id"], alex["id"]]).json()
    assert len(photo_files(data_dir)) == 6
    refs = {c["image"] for c in copies} | {template_ref := client.get(url).json()["image"]}
    assert len(refs) == 3 and template_ref.startswith("photo/")

    client.delete(url, headers=PARENT)
    assert len(photo_files(data_dir)) == 4
    for mission in copies:
        assert client.get(f"/api/missions/{mission['id']}").json()["image_url"].startswith("/api/photos/")
        assert client.get(mission["image_url"]).status_code == 200


def test_saving_a_mission_copies_its_photos(client, bea, data_dir):
    mission = create_mission(client, bea["id"]).json()
    upload(client, f"/api/missions/{mission['id']}/photo")
    template = save_as_template(client, mission["id"]).json()
    assert template["image"] != client.get(f"/api/missions/{mission['id']}").json()["image"]
    client.delete(f"/api/missions/{mission['id']}", headers=PARENT)
    assert client.get(template["image_url"]).status_code == 200


def test_deleting_a_child_keeps_the_templates(client, bea):
    mission = create_mission(client, bea["id"]).json()
    save_as_template(client, mission["id"])
    client.delete(f"/api/children/{bea['id']}", headers=PARENT)
    assert names(client.get("/api/templates").json()) == SAMPLES + ["Despegue (2)"]
