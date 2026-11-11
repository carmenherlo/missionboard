"""A copy of everything the family has (Configurar → Copia de seguridad), and putting
one back: to move to another device (or into Home Assistant) without losing anything.

A copy is one .zip with the configuration, the database (the history: stars,
missions done, the log) and the files the parents uploaded: photos, songs and avatars. Not the voice's cache or model (they are made again), nor the
automatic .bak copies of the migrations.

Putting one back is all or nothing: the copy is first checked in a folder of its
own (it opens, its versions are not newer than this app, its routines add up,
after bringing it to today's version; one from before family missions cannot be used);
only then is what there was kept as a copy
in backups/, and replaced.
"""

import io
import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

import yaml

from app.errors import InvalidError
from app.routines.repository import RoutinesRepository
from app.settings import SettingsRepository
from app.storage import db
from app.storage.config_store import CONFIG_FILENAME, ConfigStore

FOLDERS = ("photos", "sounds", "avatars")  # the files the parents uploaded
MANIFEST = "missionboard-backup.json"  # says what the zip is, and from which versions
BACKUPS_DIRNAME = "backups"  # where what there was is kept before putting a copy back
MAX_BYTES = 1024 * 1024 * 1024  # 1 GB: songs are up to 15 MB each


def filename(now: datetime) -> str:
    return f"missionboard-copia-{now:%Y-%m-%d-%H%M}.zip"


def build(data_dir: Path, now: datetime) -> bytes:
    """The whole family in one zip."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # As the app sees it (also before anything was saved: the initial one)
        config = ConfigStore(data_dir).load()
        zf.writestr(CONFIG_FILENAME, yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
        database = db.db_path(data_dir)
        if database.exists():
            zf.writestr(database.name, _database_copy(database))
        for folder in FOLDERS:
            for path in sorted((data_dir / folder).glob("*")):
                if path.is_file() and not path.name.startswith("."):
                    zf.write(path, f"{folder}/{path.name}")
        zf.writestr(MANIFEST, json.dumps({
            "app": "missionboard", "created": now.isoformat(timespec="seconds"),
            "config_version": config["version"], "db_version": len(db.MIGRATIONS),
        }, indent=2))
    return buffer.getvalue()


def restore(data_dir: Path, data: bytes, store: ConfigStore, now: datetime) -> Path:
    """Put a copy in place of what there is. Returns where what there was was kept."""
    data_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=data_dir, prefix=".restoring-") as tmp:  # same disk: moved, not copied
        incoming = Path(tmp)
        _unpack(data, incoming)
        _check(incoming)
        with store.lock():
            kept = data_dir / BACKUPS_DIRNAME / f"antes-de-restaurar-{now:%Y-%m-%d-%H%M%S}.zip"
            kept.parent.mkdir(parents=True, exist_ok=True)
            kept.write_bytes(build(data_dir, now))
            for name in (CONFIG_FILENAME, db.DB_FILENAME):
                (incoming / name).replace(data_dir / name)
            for folder in FOLDERS:
                shutil.rmtree(data_dir / folder, ignore_errors=True)
                (incoming / folder).replace(data_dir / folder)
    return kept


def _database_copy(path: Path) -> bytes:
    """The database as it is now, consistent even if it is being written."""
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / path.name
        source, target = sqlite3.connect(path), sqlite3.connect(copy)
        try:
            source.backup(target)
        finally:
            source.close()
            target.close()
        return copy.read_bytes()


def _unpack(data: bytes, into: Path) -> None:
    """Only what a copy has, and nothing outside its folder."""
    if len(data) > MAX_BYTES:
        raise InvalidError("The copy is too big")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as err:
        raise InvalidError("Not a copy of missionboard") from err
    with zf:
        names = set(zf.namelist())
        if MANIFEST not in names or CONFIG_FILENAME not in names:
            raise InvalidError("Not a copy of missionboard")
        for folder in FOLDERS:
            (into / folder).mkdir()
        for name in names - {MANIFEST}:
            path = PurePosixPath(name)
            allowed = (name in (CONFIG_FILENAME, db.DB_FILENAME)
                       or (len(path.parts) == 2 and path.parts[0] in FOLDERS and not path.name.startswith(".")))
            if not allowed:
                continue  # not part of a copy: left out
            (into / name).write_bytes(zf.read(name))


def _check(data_dir: Path) -> None:
    """As at startup: the copy is brought to today's version and must make sense."""
    try:
        store = ConfigStore(data_dir)
        store.migrate()
        db.migrate(data_dir)
        settings = SettingsRepository(store)
        settings.settings()
        settings.features()
        RoutinesRepository(store).list()
    except InvalidError:
        raise
    except Exception as err:  # newer than this app, or broken
        raise InvalidError(f"The copy cannot be used: {err}") from err
