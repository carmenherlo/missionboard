import sqlite3
from pathlib import Path

DB_FILENAME = "missionboard.db"


def db_path(data_dir: Path) -> Path:
    return data_dir / DB_FILENAME


def connect(data_dir: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(data_dir))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(data_dir: Path) -> None:
    """Create the data directory and the database file if they don't exist."""
    data_dir.mkdir(parents=True, exist_ok=True)
    with connect(data_dir) as conn:
        conn.execute("SELECT 1")
