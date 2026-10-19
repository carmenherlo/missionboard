import yaml

from app.config_store import DEFAULT_PARENT_CODE, config_path


def test_unlock_with_default_code(client):
    assert client.post("/api/parents/unlock", json={"code": DEFAULT_PARENT_CODE}).status_code == 204


def test_unlock_with_wrong_code(client):
    assert client.post("/api/parents/unlock", json={"code": "0000"}).status_code == 401


def test_unlock_uses_code_from_config(client, data_dir):
    config_path(data_dir).write_text(yaml.safe_dump({"parents": {"code": "9876"}}))
    assert client.post("/api/parents/unlock", json={"code": "9876"}).status_code == 204
    assert client.post("/api/parents/unlock", json={"code": DEFAULT_PARENT_CODE}).status_code == 401
