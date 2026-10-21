import re
from pathlib import Path

import pytest

from app.storage import db


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
    assert '<script type="module" src="/static/js/main.js">' in response.text


STATIC_DIR = Path(__file__).parent.parent / "app" / "static"
ASSETS = sorted(
    "/static/" + p.relative_to(STATIC_DIR).as_posix()
    for p in STATIC_DIR.rglob("*")
    if p.suffix in {".css", ".js"}
)


@pytest.mark.parametrize("path", ASSETS)
def test_static_assets(client, path):
    response = client.get(path)
    assert response.status_code == 200
    if path.endswith(".js"):
        assert "javascript" in response.headers["content-type"]


def test_js_imports_resolve():
    """Every relative import in a module points to a file that exists."""
    for module in STATIC_DIR.rglob("*.js"):
        for target in re.findall(r'from "(\.{1,2}/[^"]+)"', module.read_text()):
            assert (module.parent / target).resolve().is_file(), f"{module.name}: {target}"
