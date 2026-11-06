"""Starting from scratch (misiones-2): nothing from before family missions is converted.

If config.yaml is older than that, a whole copy of what there was goes to backups/,
and then the configuration and the history are removed. The song library stays (its
list and its files): songs are not easy to get again. Each family then has the
examples of a new installation.

With no config.yaml at all, a new installation: the examples (`with_samples`, only
for the real app: tests start empty).
"""

import shutil
import zipfile
from datetime import datetime
from pathlib import Path

import yaml

from app import samples
from app.storage.config_migrations import FIRST_VERSION, initial
from app.storage.config_store import CONFIG_FILENAME, ConfigStore
from app.storage.db import DB_FILENAME

BACKUPS_DIRNAME = "backups"
NOT_COPIED = {BACKUPS_DIRNAME, "voices", "voice-cache"}  # made or downloaded again
REMOVED_FOLDERS = ("photos", "backgrounds")


def run(data_dir: Path, now: datetime, with_samples: bool = False) -> bool:
    """Returns whether the examples were put in place (their children then get their first stars)."""
    config = data_dir / CONFIG_FILENAME
    songs = []
    if config.exists():
        old = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
        if old.get("version", 1) >= FIRST_VERSION:
            return False
        keep_a_copy(data_dir, now)
        songs = old.get("songs") or []
        _remove_old(data_dir)
    elif not with_samples:
        return False
    doc = samples.document() if with_samples else initial()
    ConfigStore(data_dir).replace({**doc, "songs": songs})
    return with_samples


def keep_a_copy(data_dir: Path, now: datetime) -> Path:
    copy = data_dir / BACKUPS_DIRNAME / f"antes-de-misiones-{now:%Y-%m-%d-%H%M%S}.zip"
    copy.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(copy, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(data_dir.rglob("*")):
            relative = path.relative_to(data_dir)
            if path.is_file() and relative.parts[0] not in NOT_COPIED:
                zf.write(path, relative.as_posix())
    return copy


def _remove_old(data_dir: Path) -> None:
    (data_dir / CONFIG_FILENAME).unlink()
    for path in [*data_dir.glob(f"{CONFIG_FILENAME}.v*.bak"), *data_dir.glob(f"{DB_FILENAME}*")]:
        path.unlink()
    for folder in REMOVED_FOLDERS:
        shutil.rmtree(data_dir / folder, ignore_errors=True)
