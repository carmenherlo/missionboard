import pytest
import yaml

from app.storage import config_migrations, db
from app.storage.config_store import ConfigStore, config_path

V1_FILE = {
    "version": 1,
    "parents": {"code": "1111"},
    "children": [
        {"id": "4ca2bf6b", "name": "Noa", "avatar_type": "preset", "preset": "unicorn",
         "photo": None, "color": "#9d4edd"},
    ],
}


def write_yaml(data_dir, doc):
    data_dir.mkdir(parents=True, exist_ok=True)
    config_path(data_dir).write_text(yaml.safe_dump(doc))


def read_yaml(data_dir):
    return yaml.safe_load(config_path(data_dir).read_text())


# ---------- config.yaml migrations ----------


def test_v1_file_is_upgraded_and_backed_up(tmp_path):
    write_yaml(tmp_path, V1_FILE)
    ConfigStore(tmp_path).migrate()

    doc = read_yaml(tmp_path)
    assert doc["version"] == config_migrations.CURRENT_VERSION
    assert doc["parents"] == V1_FILE["parents"]
    assert doc["children"] == [{**V1_FILE["children"][0], "color": "#9471e7"}]  # the unicorn is lilac since v5
    assert doc["settings"]["stars_per_mission"] == 1
    assert doc["features"]["games"] is False
    assert yaml.safe_load((tmp_path / "config.yaml.v1.bak").read_text()) == V1_FILE


def test_migrate_keeps_hand_written_settings(tmp_path):
    write_yaml(tmp_path, {**V1_FILE, "settings": {"stars_per_mission": 3}})
    ConfigStore(tmp_path).migrate()
    assert read_yaml(tmp_path)["settings"]["stars_per_mission"] == 3


def test_migrate_current_file_does_nothing(tmp_path):
    write_yaml(tmp_path, V1_FILE)
    store = ConfigStore(tmp_path)
    store.migrate()
    (tmp_path / "config.yaml.v1.bak").unlink()
    store.migrate()
    assert not list(tmp_path.glob("*.bak"))


def test_migrate_without_file_creates_nothing(tmp_path):
    ConfigStore(tmp_path).migrate()
    assert not config_path(tmp_path).exists()


def test_file_without_version_counts_as_v1(tmp_path):
    write_yaml(tmp_path, {"parents": {"code": "9876"}})
    doc = ConfigStore(tmp_path).load()
    assert doc["version"] == config_migrations.CURRENT_VERSION
    assert doc["parents"]["code"] == "9876"
    assert doc["children"] == []


def test_newer_file_is_refused(tmp_path):
    write_yaml(tmp_path, {**V1_FILE, "version": config_migrations.CURRENT_VERSION + 1})
    with pytest.raises(config_migrations.ConfigVersionError):
        ConfigStore(tmp_path).migrate()


def test_upgrade_does_not_share_state():
    first = config_migrations.initial()
    first["children"].append({"id": "x"})
    assert config_migrations.initial()["children"] == []


# ---------- config store editing ----------


def test_failed_edit_saves_nothing(tmp_path):
    store = ConfigStore(tmp_path)
    with pytest.raises(RuntimeError):
        with store.edit() as doc:
            doc["children"].append({"id": "x"})
            raise RuntimeError
    assert not config_path(tmp_path).exists()


def test_nested_edits_share_one_document(tmp_path):
    store = ConfigStore(tmp_path)
    with store.edit() as outer:
        with store.edit() as inner:
            inner["children"].append({"id": "a"})
        assert store.load() is outer
        assert not config_path(tmp_path).exists()  # saved once, at the end
    assert read_yaml(tmp_path)["children"] == [{"id": "a"}]


def test_failure_after_nested_edit_saves_nothing(tmp_path):
    store = ConfigStore(tmp_path)
    with pytest.raises(RuntimeError):
        with store.edit():
            with store.edit() as doc:
                doc["children"].append({"id": "a"})
            raise RuntimeError
    assert not config_path(tmp_path).exists()


# ---------- SQLite migrations ----------

MIGRATIONS = [
    "CREATE TABLE a (id INTEGER PRIMARY KEY)",
    "CREATE TABLE b (id INTEGER PRIMARY KEY)",
]


def schema_version(data_dir):
    with db.connect(data_dir) as conn:
        return conn.execute("PRAGMA user_version").fetchone()[0]


def tables(data_dir):
    with db.connect(data_dir) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return sorted(row[0] for row in rows)


def test_db_migrations_apply_in_order(tmp_path):
    db.migrate(tmp_path, MIGRATIONS[:1])
    assert schema_version(tmp_path) == 1
    assert tables(tmp_path) == ["a"]

    db.migrate(tmp_path, MIGRATIONS)
    assert schema_version(tmp_path) == 2
    assert tables(tmp_path) == ["a", "b"]
    assert (tmp_path / "missionboard.db.v1.bak").is_file()


def test_db_migrate_is_idempotent(tmp_path):
    db.migrate(tmp_path, MIGRATIONS)
    db.migrate(tmp_path, MIGRATIONS)
    assert schema_version(tmp_path) == 2


def test_failed_db_migration_keeps_previous_version(tmp_path):
    db.migrate(tmp_path, MIGRATIONS[:1])
    with pytest.raises(Exception):
        db.migrate(tmp_path, [MIGRATIONS[0], "CREATE TABLE c (id); SELECT * FROM missing"])
    assert schema_version(tmp_path) == 1
    assert tables(tmp_path) == ["a"]


def test_newer_db_is_refused(tmp_path):
    db.migrate(tmp_path, MIGRATIONS)
    with pytest.raises(db.SchemaVersionError):
        db.migrate(tmp_path, MIGRATIONS[:1])


def test_v2_file_gets_missions(tmp_path):
    write_yaml(tmp_path, {**V1_FILE, "version": 2, "settings": {}, "features": {}})
    ConfigStore(tmp_path).migrate()
    doc = read_yaml(tmp_path)
    assert doc["version"] == config_migrations.CURRENT_VERSION
    assert doc["missions"] == []
    assert [c["id"] for c in doc["children"]] == ["4ca2bf6b"]
    assert (tmp_path / "config.yaml.v2.bak").is_file()


def test_v3_file_gets_the_sample_templates(tmp_path):
    mission = {"id": "m1", "child_id": "4ca2bf6b", "name": "Despegue", "steps": []}
    write_yaml(tmp_path, {**V1_FILE, "version": 3, "settings": {}, "features": {}, "missions": [mission]})
    ConfigStore(tmp_path).migrate()
    doc = read_yaml(tmp_path)
    assert doc["version"] == config_migrations.CURRENT_VERSION
    assert doc["missions"] == [mission]
    assert [t["name"] for t in doc["templates"]] == ["Despegue", "Aterrizaje", "Alunizaje"]
    assert all("child_id" not in t for t in doc["templates"])
    assert [s["text"] for s in doc["templates"][0]["steps"]][:3] == ["Hacer la cama", "Vestirse", "Desayunar"]
    assert (tmp_path / "config.yaml.v3.bak").is_file()


def test_new_install_starts_with_the_sample_templates():
    assert [t["name"] for t in config_migrations.initial()["templates"]] == ["Despegue", "Aterrizaje", "Alunizaje"]


def test_v4_file_moves_the_children_to_the_new_palette(tmp_path):
    def child(id, color, preset=None):
        avatar = {"avatar_type": "preset", "preset": preset} if preset else {"avatar_type": "photo", "preset": None}
        return {"id": id, "name": id, "photo": None, "color": color, **avatar}

    children = [
        child("fox", "#f8961e", preset="fox"),
        child("owl", "#8d6e63", preset="owl"),
        child("lion-was-edited", "#e63946", preset="lion"),  # an animal always takes its own colour
        child("photo-purple", "#9d4edd"),
        child("photo-brown", "#8D6E63"),
        child("photo-unknown", "#123456"),  # not from the old palette: left as it was
    ]
    write_yaml(tmp_path, {**V1_FILE, "version": 4, "settings": {}, "features": {}, "missions": [],
                          "templates": [], "children": children})
    ConfigStore(tmp_path).migrate()
    doc = read_yaml(tmp_path)
    assert doc["version"] == 5
    assert {c["id"]: c["color"] for c in doc["children"]} == {
        "fox": "#e77300",
        "owl": "#244d99",
        "lion-was-edited": "#f6d700",
        "photo-purple": "#9471e7",
        "photo-brown": "#d3372f",
        "photo-unknown": "#123456",
    }
    assert [c["name"] for c in doc["children"]] == [c["name"] for c in children]
    assert (tmp_path / "config.yaml.v4.bak").is_file()
