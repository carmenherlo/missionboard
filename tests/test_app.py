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
    assert '<script type="module" src="static/js/main.js">' in response.text


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


@pytest.mark.parametrize("path", ["/", "/static/js/main.js", "/static/css/tokens.css"])
def test_app_code_is_revalidated(client, path):
    assert client.get(path).headers["cache-control"] == "no-cache"


def test_js_imports_resolve():
    """Every relative import in a module points to a file that exists."""
    for module in STATIC_DIR.rglob("*.js"):
        for target in re.findall(r'from "(\.{1,2}/[^"]+)"', module.read_text()):
            assert (module.parent / target).resolve().is_file(), f"{module.name}: {target}"


def test_fonts_ship_with_the_app(client):
    for name in ("nunito-latin.woff2", "nunito-latin-ext.woff2", "OFL.txt"):
        assert client.get(f"/static/fonts/nunito/{name}").status_code == 200, name


def test_colours_only_in_tokens():
    """Design tokens live in tokens.css; other stylesheets must not hard-code colours."""
    for sheet in (STATIC_DIR / "css").glob("*.css"):
        if sheet.name == "tokens.css":
            continue
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", sheet.read_text()), sheet.name


def test_every_theme_defines_the_roles_the_app_uses(client):
    used = set(re.findall(r"var\((--md-[\w-]+)\)", (STATIC_DIR / "css" / "tokens.css").read_text()))
    themes = sorted((STATIC_DIR / "css" / "themes").glob("*.css"))
    assert used and themes
    for theme in themes:
        defined = set(re.findall(r"(--md-[\w-]+):", theme.read_text()))
        assert used <= defined, f"{theme.name} lacks {sorted(used - defined)}"
    assert client.get("/static/css/themes/azul-mision.css").status_code == 200


def test_the_front_uses_relative_paths():
    # Under Home Assistant's ingress the page lives under a sub-path: "/api/..." or
    # "/static/..." would leave it, "api/..." and "static/..." stay inside.
    import re
    pattern = re.compile(r"""["'`(]/(api|static)/""")
    found = [f"{p.relative_to(STATIC_DIR)}:{n}" for p in STATIC_DIR.rglob("*")
             if p.suffix in (".js", ".html", ".css") and "libraries" not in p.parts
             for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1) if pattern.search(line)]
    assert found == []
