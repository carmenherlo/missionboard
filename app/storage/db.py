"""SQLite database for state and history, with versioned schema migrations."""

import shutil
import sqlite3
from pathlib import Path

DB_FILENAME = "missionboard.db"

# Schema migrations, applied in order. The schema version is the number
# applied so far (stored in PRAGMA user_version). Never edit or reorder
# an entry once released: add a new one instead.
MIGRATIONS: list[str] = []


class SchemaVersionError(Exception):
    """The database was written by a newer version of the app."""


def db_path(data_dir: Path) -> Path:
    return data_dir / DB_FILENAME


def connect(data_dir: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(data_dir))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def migrate(data_dir: Path, migrations: list[str] = MIGRATIONS) -> None:
    """Create the database if needed and apply pending migrations.

    Before upgrading an existing schema, a copy of the file is kept.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    with connect(data_dir) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version > len(migrations):
        raise SchemaVersionError(
            f"Database is version {version}; this app understands up to {len(migrations)}"
        )
    if version == len(migrations):
        return

    path = db_path(data_dir)
    if version > 0:
        shutil.copy2(path, path.with_name(f"{path.name}.v{version}.bak"))
    conn = connect(data_dir)
    try:
        for number, sql in enumerate(migrations[version:], start=version + 1):
            # executescript commits on its own, so each migration and its
            # version bump go in one explicit transaction.
            conn.executescript(f"BEGIN; {sql}; PRAGMA user_version = {number}; COMMIT;")
    finally:
        conn.close()
