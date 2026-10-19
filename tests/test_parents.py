import pytest
import yaml

from app.config_store import DEFAULT_PARENT_CODE, config_path
from tests.conftest import PARENT


def test_unlock_with_default_code(client):
    assert client.post("/api/parents/unlock", json={"code": DEFAULT_PARENT_CODE}).status_code == 204


def test_unlock_with_wrong_code(client):
    assert client.post("/api/parents/unlock", json={"code": "0000"}).status_code == 401


def test_unlock_uses_code_from_config(client, data_dir):
    config_path(data_dir).write_text(yaml.safe_dump({"parents": {"code": "9876"}}))
    assert client.post("/api/parents/unlock", json={"code": "9876"}).status_code == 204
    assert client.post("/api/parents/unlock", json={"code": DEFAULT_PARENT_CODE}).status_code == 401


def test_change_code(client, data_dir):
    response = client.put("/api/parents/code", json={"code": "24680"}, headers=PARENT)
    assert response.status_code == 204
    assert yaml.safe_load(config_path(data_dir).read_text())["parents"]["code"] == "24680"
    assert client.post("/api/parents/unlock", json={"code": "24680"}).status_code == 204
    assert client.post("/api/parents/unlock", json={"code": DEFAULT_PARENT_CODE}).status_code == 401


def test_change_code_keeps_children(client, data_dir):
    client.post(
        "/api/children",
        json={"name": "Bea", "avatar_type": "preset", "preset": "unicorn"},
        headers=PARENT,
    )
    client.put("/api/parents/code", json={"code": "2468"}, headers=PARENT)
    assert [c["name"] for c in client.get("/api/children").json()] == ["Bea"]


def test_change_code_requires_current_code(client):
    response = client.put("/api/parents/code", json={"code": "2468"}, headers={"X-Parent-Code": "0000"})
    assert response.status_code == 401
    assert client.put("/api/parents/code", json={"code": "2468"}).status_code == 401


@pytest.mark.parametrize("code", ["123", "123456789", "12a4", " 1234", ""])
def test_change_code_rejects_invalid(client, code):
    response = client.put("/api/parents/code", json={"code": code}, headers=PARENT)
    assert response.status_code == 422
