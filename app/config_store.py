"""Family configuration stored in data/config.yaml (the source of truth)."""

import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path

import yaml

CONFIG_FILENAME = "config.yaml"
CONFIG_VERSION = 1
DEFAULT_PARENT_CODE = "1234"

_lock = threading.Lock()


def config_path(data_dir: Path) -> Path:
    return data_dir / CONFIG_FILENAME


def default_config() -> dict:
    return {
        "version": CONFIG_VERSION,
        "parents": {"code": DEFAULT_PARENT_CODE},
        "children": [],
    }


def load(data_dir: Path) -> dict:
    config = default_config()
    path = config_path(data_dir)
    if path.exists():
        with path.open(encoding="utf-8") as f:
            config.update(yaml.safe_load(f) or {})
    return config


def save(data_dir: Path, config: dict) -> None:
    """Write the config atomically so a crash never leaves a half-written file."""
    data_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=data_dir, prefix=".config-", suffix=".yaml")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False)
        os.replace(tmp, config_path(data_dir))
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


@contextmanager
def edit(data_dir: Path):
    """Load, let the caller mutate, and save. Nothing is saved if the block raises."""
    with _lock:
        config = load(data_dir)
        yield config
        save(data_dir, config)


def parent_code(config: dict) -> str:
    return str((config.get("parents") or {}).get("code", DEFAULT_PARENT_CODE))
