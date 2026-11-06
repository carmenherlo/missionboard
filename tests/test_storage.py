import pytest
import yaml

from app.storage import config_migrations, db
from app.storage.config_store import ConfigStore, config_path

CURRENT = {
    "version": config_migrations.CURRENT_VERSION,
    "parents": {"code": "1111"},
    "children": [{"id": "4ca2bf6b", "name": "Noa", "preset": "unicorn", "color": "#9471e7"}],
}


def write_yaml(data_dir, doc):
    data_dir.mkdir(parents=True, exist_ok=True)
    config_path(data_dir).write_text(yaml.safe_dump(doc))


def read_yaml(data_dir):
    return yaml.safe_load(config_path(data_dir).read_text())


# ---------- config.yaml migrations ----------


def test_a_migration_is_applied_and_the_old_file_kept(tmp_path, monkeypatch):
    version = config_migrations.CURRENT_VERSION
    write_yaml(tmp_path, CURRENT)
    monkeypatch.setattr(config_migrations, "CURRENT_VERSION", version + 1)
    monkeypatch.setitem(config_migrations._MIGRATIONS, version, lambda doc: {**doc, "version": version + 1, "new": True})
    ConfigStore(tmp_path).migrate()
    doc = read_yaml(tmp_path)
    assert doc["version"] == version + 1 and doc["new"] is True and doc["parents"] == CURRENT["parents"]
    assert yaml.safe_load((tmp_path / f"config.yaml.v{version}.bak").read_text()) == CURRENT


def test_migrate_current_file_does_nothing(tmp_path):
    write_yaml(tmp_path, CURRENT)
    ConfigStore(tmp_path).migrate()
    assert not list(tmp_path.glob("*.bak"))


def test_migrate_without_file_creates_nothing(tmp_path):
    ConfigStore(tmp_path).migrate()
    assert not config_path(tmp_path).exists()


def test_missing_keys_of_a_hand_written_file_are_filled(tmp_path):
    write_yaml(tmp_path, {"version": config_migrations.CURRENT_VERSION, "parents": {"code": "9876"}})
    doc = ConfigStore(tmp_path).load()
    assert doc["parents"]["code"] == "9876" and doc["children"] == []


def test_a_file_from_before_family_missions_is_not_converted(tmp_path):
    write_yaml(tmp_path, {"parents": {"code": "9876"}})
    with pytest.raises(config_migrations.ConfigTooOldError):
        ConfigStore(tmp_path).load()


def test_newer_file_is_refused(tmp_path):
    write_yaml(tmp_path, {**CURRENT, "version": config_migrations.CURRENT_VERSION + 1})
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
