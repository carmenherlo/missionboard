from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

from app.storage import db
from app.storage.config_store import ConfigStore


@dataclass
class ShopItem:
    """Something the stars buy ("Un globo", 5 stars), the same for every child."""

    id: str
    text: str
    price: int
    image: str | None = None
    image_suggested: bool = False


def _from_doc(entry: dict) -> ShopItem:
    return ShopItem(
        id=entry["id"],
        text=entry["text"],
        price=int(entry.get("price", 1)),
        image=entry.get("image"),
        image_suggested=bool(entry.get("image_suggested", False)),
    )


class ShopRepository:
    """The `shop` list of config.yaml."""

    def __init__(self, store: ConfigStore):
        self._store = store

    def atomic(self):
        return self._store.edit()

    def list(self) -> list[ShopItem]:
        return [_from_doc(entry) for entry in self._store.load().get("shop") or []]

    def get(self, item_id: str) -> ShopItem | None:
        return next((i for i in self.list() if i.id == item_id), None)

    def add(self, item: ShopItem) -> None:
        with self._store.edit() as doc:
            doc.setdefault("shop", []).append(asdict(item))

    def update(self, item: ShopItem) -> None:
        with self._store.edit() as doc:
            doc["shop"] = [asdict(item) if e["id"] == item.id else e for e in doc["shop"]]

    def remove(self, item_id: str) -> None:
        with self._store.edit() as doc:
            doc["shop"] = [e for e in doc["shop"] if e["id"] != item_id]


class PurchasesRepository:
    """What each child bought (SQLite), and its stars going out of their bank."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def buy(self, day: date, child, item: ShopItem, at: datetime) -> int | None:
        """The purchase and its stars, in one transaction, only if the child has enough.
        Its id (the order's), or None."""
        with db.connect(self._data_dir) as conn:
            balance = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM star_movements WHERE child_id = ?", (child.id,)
            ).fetchone()[0]
            if balance < item.price:
                return None
            stamp = at.isoformat(timespec="seconds")
            cursor = conn.execute(
                "INSERT INTO purchases (day, child_id, child_name, item_id, item_text, item_image, price, at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (day.isoformat(), child.id, child.name, item.id, item.text, item.image, item.price, stamp),
            )
            conn.execute(
                "INSERT INTO star_movements (child_id, child_name, amount, reason, mission_id, mission_name, day, at)"
                " VALUES (?, ?, ?, 'purchase', ?, ?, ?, ?)",
                (child.id, child.name, -item.price, item.id, item.text, day.isoformat(), stamp),
            )
        return cursor.lastrowid

    # ---------- orders (tienda-2.html) ----------

    def get(self, order_id: int) -> dict | None:
        with db.connect(self._data_dir) as conn:
            row = conn.execute("SELECT * FROM purchases WHERE id = ?", (order_id,)).fetchone()
        return dict(row) if row else None

    def of_child(self, child_id: str, done_limit: int) -> list[dict]:
        """On their way and arrived but not seen yet (oldest first), then the latest seen."""
        with db.connect(self._data_dir) as conn:
            open_ = conn.execute(
                "SELECT * FROM purchases WHERE child_id = ? AND seen_at IS NULL ORDER BY id", (child_id,)
            ).fetchall()
            done = conn.execute(
                "SELECT * FROM purchases WHERE child_id = ? AND seen_at IS NOT NULL ORDER BY id DESC LIMIT ?",
                (child_id, done_limit),
            ).fetchall()
        return [dict(row) for row in [*open_, *done]]

    def waiting(self) -> list[dict]:
        """Every order not handed over yet, oldest first."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute("SELECT * FROM purchases WHERE delivered_at IS NULL ORDER BY id").fetchall()
        return [dict(row) for row in rows]

    def handed_over(self, limit: int) -> list[dict]:
        with db.connect(self._data_dir) as conn:
            rows = conn.execute(
                "SELECT * FROM purchases WHERE delivered_at IS NOT NULL ORDER BY delivered_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def not_seen(self) -> list[dict]:
        """On their way or arrived and not seen: what the children's screens point at."""
        with db.connect(self._data_dir) as conn:
            rows = conn.execute("SELECT * FROM purchases WHERE seen_at IS NULL ORDER BY id").fetchall()
        return [dict(row) for row in rows]

    def set(self, order_id: int, **fields) -> None:
        """due_day, delivered_at, seen_at or reminded_day (ISO texts or None)."""
        assert set(fields) <= {"due_day", "delivered_at", "seen_at", "reminded_day"}
        columns = ", ".join(f"{name} = ?" for name in fields)
        with db.connect(self._data_dir) as conn:
            conn.execute(f"UPDATE purchases SET {columns} WHERE id = ?", (*fields.values(), order_id))
