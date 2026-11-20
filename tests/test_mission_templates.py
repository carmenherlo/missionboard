"""Mission templates: a new mission as a copy of one the app brings (primer-arranque.html)."""

from tests.conftest import PARENT


def templates(client):
    return client.get("/api/mission-templates").json()


def use(client, template_id, headers=PARENT):
    return client.post(f"/api/mission-templates/{template_id}/use", headers=headers)


def test_the_app_brings_three_templates_with_their_tasks(client):
    found = templates(client)
    assert [t["name"] for t in found] == ["Despegue", "Aterrizaje", "Alunizaje"]
    assert all(t["image_url"] and t["colors"] and t["tasks"] for t in found)
    assert found[0]["tasks"][0]["text"] == "Despertarse"


def test_using_one_makes_a_mission_of_the_family_always_open_and_on_for_every_child(client):
    bea = client.post("/api/children", json={"name": "Bea", "preset": "fox"}, headers=PARENT).json()
    response = use(client, "despegue")
    assert response.status_code == 201
    mission = response.json()
    assert mission["name"] == "Despegue" and mission["schedule"] is None
    assert mission["id"] != "despegue" and mission["routine"] is None
    assert len(mission["tasks"]) == 7
    counts = mission["children"][0]
    assert counts["id"] == bea["id"] and counts["active"] == counts["total"] > 0
    assert [m["id"] for m in client.get("/api/missions").json()] == [mission["id"]]


def test_a_copy_is_independent_and_a_second_one_gets_another_name_and_ids(client):
    first = use(client, "alunizaje").json()
    second = use(client, "alunizaje").json()
    assert second["name"] == "Alunizaje (2)"
    ids = lambda m: {m["id"], *(t["id"] for t in m["tasks"]), *(s["id"] for t in m["tasks"] for s in t["steps"])}  # noqa: E731
    assert not ids(first) & ids(second)
    client.patch(f"/api/missions/{first['id']}", json={"name": "Noche"}, headers=PARENT)
    assert templates(client)[2]["name"] == "Alunizaje"


def test_only_parents_use_a_template_and_an_unknown_one_is_not_found(client):
    assert use(client, "despegue", headers={}).status_code == 401
    assert use(client, "nope").status_code == 404
