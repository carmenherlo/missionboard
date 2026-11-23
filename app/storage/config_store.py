"""Family configuration stored in config.yaml (the source of truth).

Only this module knows the file format. Repositories on top of it expose
each section (children, parents, settings...) as plain Python objects.
"""

import copy
import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path

import yaml

from app.storage import config_migrations

CONFIG_FILENAME = "config.yaml"
# libyaml's safe loader when PyYAML was built with it (about ten times faster), else Python's.
FAST_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def config_path(data_dir: Path) -> Path:
    return data_dir / CONFIG_FILENAME


class ConfigStore:
    def __init__(self, data_dir: Path):
        self.path = config_path(data_dir)
        self._lock = threading.RLock()
        self._local = threading.local()
        # The last document read and the file it came from: parsed again only when the file
        # changes (another device saved, or someone edited it by hand). Callers get a copy.
        self._cached: tuple[tuple, dict] | None = None

    def migrate(self) -> None:
        """Bring the file to the current version, keeping a copy of the old one."""
        with self._lock:
            if not self.path.exists():
                return
            raw = self._read()
            version = raw.get("version", 1)
            upgraded = config_migrations.upgrade(raw)
            if version != upgraded["version"]:
                shutil.copy2(self.path, self.path.with_name(f"{self.path.name}.v{version}.bak"))
                self._write(upgraded)

    def replace(self, doc: dict) -> None:
        """A whole new document (starting from scratch)."""
        with self._lock:
            self._write(doc)

    @contextmanager
    def lock(self):
        """Nobody reads or writes the file meanwhile (putting a copy back)."""
        with self._lock:
            yield

    def load(self) -> dict:
        """Current document. Inside edit(), it is the one being edited."""
        doc = getattr(self._local, "doc", None)
        if doc is not None:
            return doc
        with self._lock:
            return self._read_current()

    @contextmanager
    def edit(self):
        """Load, let the caller mutate, and save once at the end.

        Nested edits on the same thread share the document, so several
        repository calls can form one atomic change. Nothing is saved if
        the block raises.
        """
        doc = getattr(self._local, "doc", None)
        if doc is not None:
            yield doc
            return
        with self._lock:
            self._local.doc = self._read_current()
            try:
                yield self._local.doc
                self._write(self._local.doc)
            finally:
                self._local.doc = None

    def _read_current(self) -> dict:
        if not self.path.exists():
            return config_migrations.initial()
        stamp = self._stamp()
        if self._cached is None or self._cached[0] != stamp:
            self._cached = (stamp, config_migrations.upgrade(self._read()))
        return copy.deepcopy(self._cached[1])

    def _stamp(self) -> tuple:
        """What changes whenever the file does: every save replaces it (a new inode)."""
        info = self.path.stat()
        return (info.st_ino, info.st_mtime_ns, info.st_size)

    def _read(self) -> dict:
        with self.path.open(encoding="utf-8") as f:
            return yaml.load(f, Loader=FAST_LOADER) or {}

    def _write(self, doc: dict) -> None:
        """Write atomically so a crash never leaves a half-written file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".config-", suffix=".yaml")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
            os.replace(tmp, self.path)
            self._cached = (self._stamp(), copy.deepcopy(doc))
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
