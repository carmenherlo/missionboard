import pytest
import yaml

from app.parents.repository import DEFAULT_PARENT_CODE
from app.storage.config_store import config_path
from tests.conftest import PARENT


def test_unlock_with_default_code(client):
    assert client.post("/api/parents/unlock", json={"code": DEFAULT_PARENT_CODE}).status_code == 204


def test_unlock_with_wrong_code(client):
    assert client.post("/api/parents/unlock", json={"code": "0000"}).status_code == 401


def test_unlock_uses_code_from_config(client, data_dir):
    config_path(data_dir).write_text(yaml.safe_dump({"parents": {"code": "9876"}}))
    assert client.post("/api/parents/unlock", json={"code": "9876"}).status_code == 204
    assert client.post("/api/parents/unlock", json={"code": DEFAULT_PARENT_CODE}).status_code == 401


def change_code(client, code, current_code=DEFAULT_PARENT_CODE, headers=PARENT):
    return client.put(
        "/api/parents/code", json={"current_code": current_code, "code": code}, headers=headers
    )


def test_change_code(client, data_dir):
    assert change_code(client, "24680").status_code == 204
    assert yaml.safe_load(config_path(data_dir).read_text())["parents"]["code"] == "24680"
    assert client.post("/api/parents/unlock", json={"code": "24680"}).status_code == 204
    assert client.post("/api/parents/unlock", json={"code": DEFAULT_PARENT_CODE}).status_code == 401


def test_change_code_keeps_children(client):
    client.post(
        "/api/children",
        json={"name": "Bea", "avatar_type": "preset", "preset": "unicorn"},
        headers=PARENT,
    )
    change_code(client, "2468")
    assert [c["name"] for c in client.get("/api/children").json()] == ["Bea"]


def test_change_code_requires_unlocked_session(client):
    assert change_code(client, "2468", headers={"X-Parent-Code": "0000"}).status_code == 401
    assert change_code(client, "2468", headers={}).status_code == 401


def test_change_code_rejects_wrong_current_code(client, data_dir):
    assert change_code(client, "2468", current_code="0000").status_code == 403
    assert not config_path(data_dir).exists()


@pytest.mark.parametrize("code", ["123", "123456789", "12a4", " 1234", ""])
def test_change_code_rejects_invalid(client, code):
    assert change_code(client, code).status_code == 422
