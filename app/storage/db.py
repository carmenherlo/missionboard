"""SQLite database for state and history, with versioned schema migrations."""

import shutil
import sqlite3
from pathlib import Path

DB_FILENAME = "missionboard.db"

# Schema migrations, applied in order. The schema version is the number
# applied so far (stored in PRAGMA user_version). Never edit or reorder
# an entry once released: add a new one instead. No trailing "--" comments:
# migrate() appends the version bump after each script.
MIGRATIONS: list[str] = [
    # 1 · The event log: what happens in the app, with a copy of the names
    # at that moment (history must not depend on the configuration).
    """
    CREATE TABLE events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        at TEXT NOT NULL,
        day TEXT NOT NULL,
        zone TEXT NOT NULL,
        type TEXT NOT NULL,
        subject TEXT,
        action TEXT,
        child_id TEXT,
        child_name TEXT,
        mission_id TEXT,
        mission_name TEXT,
        step_id TEXT,
        step_text TEXT,
        detail TEXT
    );
    CREATE INDEX events_day ON events (day)
    """,
    # 2 · A child's day: the steps checked and the missions completed, per
    # app day (a new day starts empty), and every star won or spent as a
    # movement of their piggy bank (the balance is the sum).
    """
    CREATE TABLE step_checks (
        day TEXT NOT NULL,
        child_id TEXT NOT NULL,
        mission_id TEXT NOT NULL,
        step_id TEXT NOT NULL,
        at TEXT NOT NULL,
        PRIMARY KEY (day, child_id, mission_id, step_id)
    );
    CREATE TABLE mission_completions (
        day TEXT NOT NULL,
        child_id TEXT NOT NULL,
        mission_id TEXT NOT NULL,
        child_name TEXT,
        mission_name TEXT,
        stars INTEGER NOT NULL,
        at TEXT NOT NULL,
        PRIMARY KEY (day, child_id, mission_id)
    );
    CREATE TABLE star_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        child_id TEXT NOT NULL,
        child_name TEXT,
        amount INTEGER NOT NULL,
        reason TEXT NOT NULL,
        mission_id TEXT,
        mission_name TEXT,
        day TEXT NOT NULL,
        at TEXT NOT NULL
    );
    CREATE INDEX star_movements_child ON star_movements (child_id)
    """,
    # 3 · The daily prize: what each child won each day on the wheel, with a
    # copy of the prize as it was (prizes can be renamed or deleted later).
    """
    CREATE TABLE prize_spins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day TEXT NOT NULL,
        child_id TEXT NOT NULL,
        child_name TEXT,
        prize_id TEXT,
        prize_text TEXT NOT NULL,
        prize_image TEXT,
        at TEXT NOT NULL
    );
    CREATE INDEX prize_spins_day ON prize_spins (day, child_id)
    """,
    # 4 · Routines: what happened to each routine each day, so it does not
    # ring again once stopped, closed or finished (on any device).
    """
    CREATE TABLE routine_runs (
        day TEXT NOT NULL,
        routine_id TEXT NOT NULL,
        started_at TEXT,
        stopped_at TEXT,
        closed_phase TEXT,
        finished_at TEXT,
        PRIMARY KEY (day, routine_id)
    )
    """,
    # 5 · A routine started by hand remembers who it is with (JSON list of child ids).
    """
    ALTER TABLE routine_runs ADD COLUMN kids TEXT
    """,
    # 6 · The shop: what each child bought, with a copy of the item as it was;
    # delivered_at is set once a parent hands it over (step 7).
    """
    CREATE TABLE purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day TEXT NOT NULL,
        child_id TEXT NOT NULL,
        child_name TEXT,
        item_id TEXT,
        item_text TEXT NOT NULL,
        item_image TEXT,
        price INTEGER NOT NULL,
        at TEXT NOT NULL,
        delivered_at TEXT
    );
    CREATE INDEX purchases_child ON purchases (child_id)
    """,
    # 7 · A mission a parent has opened for a child, only that day.
    """
    CREATE TABLE mission_openings (
        day TEXT NOT NULL,
        child_id TEXT NOT NULL,
        mission_id TEXT NOT NULL,
        at TEXT NOT NULL,
        PRIMARY KEY (day, child_id, mission_id)
    )
    """,
    # 8 · A purchase is an order on its way (tienda-2.html): the day a parent says it
    # arrives, when the child saw it arrive, and the last day the parents' phones were
    # reminded. Those already handed over count as seen.
    """
    ALTER TABLE purchases ADD COLUMN due_day TEXT;
    ALTER TABLE purchases ADD COLUMN seen_at TEXT;
    ALTER TABLE purchases ADD COLUMN reminded_day TEXT;
    UPDATE purchases SET seen_at = delivered_at WHERE delivered_at IS NOT NULL
    """,
    # 9 · Padres · Hoy (step 7): a prize of the wheel handed over by a parent.
    """
    ALTER TABLE prize_spins ADD COLUMN delivered_at TEXT
    """,
]


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
