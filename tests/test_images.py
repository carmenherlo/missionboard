import pytest

from app.images.libraries import LIBRARIES, ImageLibraries, photo_filename


def test_catalog_endpoint(client):
    libraries = client.get("/api/images").json()["libraries"]
    assert [lib["id"] for lib in libraries] == ["fluent"]
    fluent = libraries[0]
    assert fluent["base_url"] == "static/libraries/fluent"
    assert len(fluent["items"]) > 1000
    assert fluent["featured"]


def test_every_catalog_item_has_its_image():
    for library in LIBRARIES:
        files = {p.stem for p in library.directory.glob("*.svg")}
        assert library.item_ids <= files, library.id
        for item in library.catalog["items"]:
            assert item["name"] and isinstance(item["keywords"], list)


def test_featured_items_exist():
    for library in LIBRARIES:
        for theme in library.catalog["featured"]:
            assert set(theme["items"]) <= library.item_ids, theme["name"]


def test_spanish_keywords():
    items = {i["id"]: i for i in LIBRARIES[0].catalog["items"]}
    assert items["toothbrush"]["name"] == "cepillo de dientes"
    assert "dientes" in items["toothbrush"]["keywords"]
    assert "cole" in items["backpack"]["keywords"]


def test_licenses_ship_with_the_library():
    for library in LIBRARIES:
        assert list(library.directory.glob("LICENSE*")), library.id


@pytest.mark.parametrize(
    "ref, url",
    [
        ("fluent/rocket", "static/libraries/fluent/rocket.svg"),
        ("fluent/nope", None),
        ("gone/rocket", None),
        ("photo/ab-cd.jpg", "api/photos/ab-cd.jpg"),
        (None, None),
    ],
)
def test_image_urls(ref, url):
    assert ImageLibraries(LIBRARIES).url(ref) == url


def test_photo_filename():
    assert photo_filename("photo/ab.jpg") == "ab.jpg"
    assert photo_filename("fluent/rocket") is None
    assert photo_filename(None) is None
