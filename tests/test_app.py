import pytest

from app import db


def test_startup_creates_database(client, data_dir):
    assert db.db_path(data_dir).is_file()


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "/static/js/app.js" in response.text


@pytest.mark.parametrize("path", ["/static/css/style.css", "/static/js/app.js"])
def test_static_assets(client, path):
    assert client.get(path).status_code == 200
