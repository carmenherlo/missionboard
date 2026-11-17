from datetime import datetime
from pathlib import Path

from app.storage import db


class MomentsRepository:
    """Momentos de vales (vales-2.html), in SQLite: when a parent opened one and until when
    (`voucher_moments`), and the gift card each child picked in it (`voucher_picks`, with a
    copy of the prize's text). Whether a card is used is its prize's delivered_at."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def current(self, now: datetime) -> dict | None:
        """The moment open now, if any."""
        with db.connect(self._data_dir) as conn:
            row = conn.execute(
                "SELECT * FROM voucher_moments WHERE ended_at IS NULL AND ends_at > ? ORDER BY id DESC LIMIT 1",
                (_at(now),),
            ).fetchone()
        return dict(row) if row else None

    def start(self, now: datetime, ends: datetime) -> None:
        with db.connect(self._data_dir) as conn:
            conn.execute("UPDATE voucher_moments SET ended_at = ? WHERE ended_at IS NULL", (_at(now),))
            conn.execute("INSERT INTO voucher_moments (started_at, ends_at) VALUES (?, ?)", (_at(now), _at(ends)))

    def end(self, now: datetime) -> bool:
        """False if none was open."""
        with db.connect(self._data_dir) as conn:
            cursor = conn.execute(
                "UPDATE voucher_moments SET ended_at = ? WHERE ended_at IS NULL AND ends_at > ?", (_at(now), _at(now))
            )
        return cursor.rowcount > 0

    def picks(self, moment_id: int) -> list[dict]:
        with db.connect(self._data_dir) as conn:
            rows = conn.execute("SELECT * FROM voucher_picks WHERE moment_id = ? ORDER BY id", (moment_id,)).fetchall()
        return [dict(row) for row in rows]

    def pick(self, pick_id: int) -> dict | None:
        with db.connect(self._data_dir) as conn:
            row = conn.execute("SELECT * FROM voucher_picks WHERE id = ?", (pick_id,)).fetchone()
        return dict(row) if row else None

    def add_pick(self, moment_id: int, child, voucher: dict, now: datetime) -> None:
        with db.connect(self._data_dir) as conn:
            conn.execute(
                "INSERT INTO voucher_picks (moment_id, child_id, child_name, voucher_id, prize_text, at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (moment_id, child.id, child.name, voucher["id"], voucher["text"], _at(now)),
            )

    def remove_pick(self, pick_id: int) -> None:
        with db.connect(self._data_dir) as conn:
            conn.execute("DELETE FROM voucher_picks WHERE id = ?", (pick_id,))


def _at(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")
